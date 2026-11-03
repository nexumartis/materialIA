"""Webhooks salientes: el dueño registra un endpoint HTTPS y recibe eventos del negocio para
conectar sus sistemas (planilla, ERP, CRM, Zapier/Make).

- **Outbox:** `enqueue` guarda el evento en la MISMA transacción que el cambio (si el pago se revierte,
  el evento tampoco existe). El worker (`deliver_due`) lo entrega con reintentos espaciados.
- **Firma:** `X-PV-Signature: t=<unix>,v1=<hex>` con HMAC-SHA256(secreto, "<t>.<cuerpo>"). El
  receptor verifica la firma y rechaza `t` viejos (repetición); `X-PV-Delivery` es único por envío
  (idempotencia del lado del receptor). El secreto se muestra UNA vez al crear el endpoint.
- **SSRF:** sólo https hacia IPs públicas, conectando a la IP verificada, sin seguir redirecciones,
  con tiempo corto y sin leer más de 4 KB de respuesta.
- **Datos mínimos:** pedido (número, estado, montos, ítems), id de conversación, calificación. Nunca
  tokens del comprador, teléfonos ni notas internas.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any, Optional

import httpx

from ..db import system_tx, tenant_tx
from . import opportunities, safe_http

log = logging.getLogger(__name__)

EVENTS = ("order.paid", "order.deposit_paid", "order.cancelled", "conversation.needs_human", "order.rated")
MAX_ENDPOINTS = 3
TIMEOUT_S = 5.0
RETRY_DELAYS_S = (60, 300, 1800, 7200, 21600)       # 1 min, 5 min, 30 min, 2 h, 6 h; después: failed
WORKER_BATCH = 50
WORKER_BUDGET_S = 30.0


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    if len(url) > 500:
        raise ValueError("El link es demasiado largo.")
    try:
        safe_http.pinned(url)
    except safe_http.UnsafeURL:
        raise ValueError("El endpoint tiene que ser https:// y apuntar a un servidor público.") from None
    except LookupError:
        raise ValueError("No encontré ese servidor. Revisá el link.") from None
    return url


def _view(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(row["id"]), "url": row["url"], "events": list(row["events"]), "active": row["active"],
            "created_at": row["created_at"].isoformat(),
            "last_success_at": row["last_success_at"].isoformat() if row["last_success_at"] else None,
            "last_error": row["last_error"]}


def list_endpoints(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute("select id, url, events, active, created_at, last_success_at, last_error from webhook_endpoints "
                "where tenant_id = %s order by created_at", (tenant_id,))
    return [_view(r) for r in cur.fetchall()]


def create(cur: Any, tenant_id: str, uid: str, url: str, events: Optional[list[str]]) -> dict[str, Any]:
    """Registra un endpoint y devuelve su secreto (única vez que se muestra)."""
    url = _validate_url(url)
    chosen = sorted(set(EVENTS if events is None else events))     # [] explícito = error, no «todos»
    if not chosen or any(e not in EVENTS for e in chosen):
        raise ValueError("Elegí eventos válidos.")
    # Bloquea el negocio: dos altas simultáneas no pasan el tope.
    cur.execute("select 1 from tenants where id = %s for update", (tenant_id,))
    cur.execute("select count(*) as n from webhook_endpoints where tenant_id = %s", (tenant_id,))
    if cur.fetchone()["n"] >= MAX_ENDPOINTS:
        raise ValueError(f"Podés tener hasta {MAX_ENDPOINTS} endpoints.")
    secret = "whsec_" + secrets.token_urlsafe(32)
    cur.execute("insert into webhook_endpoints (tenant_id, url, secret, events, created_by) values (%s, %s, %s, %s, %s) "
                "returning id, url, events, active, created_at, last_success_at, last_error",
                (tenant_id, url, secret, chosen, uid))
    view = _view(cur.fetchone())
    opportunities._audit(cur, tenant_id, "webhook_created", view["id"], {"actor": uid, "events": chosen})
    return {**view, "secret": secret}


def delete(cur: Any, tenant_id: str, uid: str, endpoint_id: str) -> bool:
    cur.execute("delete from webhook_endpoints where tenant_id = %s and id = %s", (tenant_id, endpoint_id))
    if not cur.rowcount:
        return False
    opportunities._audit(cur, tenant_id, "webhook_deleted", endpoint_id, {"actor": uid})
    return True


def deliveries(cur: Any, tenant_id: str, limit: int = 30) -> list[dict[str, Any]]:
    cur.execute("select id, endpoint_id, event, status, attempts, last_status_code, last_error, created_at, sent_at "
                "from webhook_deliveries where tenant_id = %s order by created_at desc limit %s", (tenant_id, limit))
    return [{"id": str(r["id"]), "endpoint_id": str(r["endpoint_id"]), "event": r["event"], "status": r["status"],
             "attempts": r["attempts"], "last_status_code": r["last_status_code"], "last_error": r["last_error"],
             "created_at": r["created_at"].isoformat(),
             "sent_at": r["sent_at"].isoformat() if r["sent_at"] else None} for r in cur.fetchall()]


# --- Encolar (dentro de la transacción del cambio) ---------------------------------------
def enqueue(cur: Any, tenant_id: str, event: str, data: dict[str, Any]) -> int:
    """Un envío pendiente por endpoint activo suscripto al evento. Nunca rompe la operación."""
    if event not in EVENTS:
        raise ValueError(event)
    payload = json.dumps({"event": event, "created_at": int(time.time()), "data": data}, ensure_ascii=False,
                         default=str)
    cur.execute("insert into webhook_deliveries (tenant_id, endpoint_id, event, payload) "
                "select tenant_id, id, %s, %s::jsonb from webhook_endpoints "
                "where tenant_id = %s and active and %s = any(events)", (event, payload, tenant_id, event))
    return cur.rowcount


def _subscribed(cur: Any, tenant_id: str, event: str) -> bool:
    cur.execute("select 1 from webhook_endpoints where tenant_id = %s and active and %s = any(events) limit 1",
                (tenant_id, event))
    return cur.fetchone() is not None


def enqueue_order(cur: Any, tenant_id: str, event: str, order_id: str, **extra: Any) -> int:
    """Evento de un pedido. Sólo arma el pedido si alguien está suscripto (la mayoría no). Viaja lo
    mínimo: número, estado, montos e ítems; nunca links de pago ni datos del comprador."""
    if not _subscribed(cur, tenant_id, event):
        return 0
    from . import orders     # aquí y no arriba: orders importa webhooks (ciclo)
    row = orders._fetch(cur, tenant_id, order_id)
    view = orders._view(cur, row)
    data = {"order_id": view["id"], "number": view["number"], "status": view["status"], "total": view["total"],
            "currency": view["currency"], "deposit": view.get("deposit"), "amount_due": view.get("amount_due"),
            "conversation_id": str(row["conversation_id"]) if row["conversation_id"] else None,
            "items": [{"sku": i["sku"], "name": i["name"], "qty": i["qty"], "unit_price": i["unit_price"]}
                      for i in view["items"]], **extra}
    return enqueue(cur, tenant_id, event, data)


# --- Entrega (worker) ------------------------------------------------------------------
def sign(secret: str, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"


def _post(url: str, secret: str, delivery_id: str, event: str, body: bytes) -> tuple[Optional[int], Optional[str]]:
    """(código HTTP, error). 2xx = entregado. Conecta a la IP verificada; no sigue redirecciones."""
    try:
        target, host, sni = safe_http.pinned(url)
    except (safe_http.UnsafeURL, LookupError):
        return None, "destino no público o inexistente"
    ts = int(time.time())
    headers = {**host, "Content-Type": "application/json", "User-Agent": "PresupuestoVivo-Webhooks/1",
               "X-PV-Event": event, "X-PV-Delivery": delivery_id, "X-PV-Signature": sign(secret, ts, body)}
    try:
        with httpx.Client(timeout=TIMEOUT_S, follow_redirects=False) as client:
            with client.stream("POST", target, content=body, headers=headers, extensions=sni) as r:
                for _ in r.iter_bytes(4096):
                    break                                   # no se lee más que el comienzo
                return r.status_code, None if 200 <= r.status_code < 300 else f"HTTP {r.status_code}"
    except Exception as exc:  # noqa: BLE001 - cualquier falla cuenta como intento fallido (nunca reintento eterno)
        return None, type(exc).__name__


def deliver_due(limit: int = WORKER_BATCH, budget_s: float = WORKER_BUDGET_S) -> int:
    """Entrega los envíos vencidos, de a uno. Cada envío se RECLAMA corriendo su próximo intento 2
    minutos (dos workers no lo mandan a la vez) y el POST se hace fuera de la transacción: la base no
    queda esperando a un servidor ajeno."""
    started, done = time.monotonic(), 0
    while done < limit and time.monotonic() - started < budget_s:
        with system_tx() as cur:
            cur.execute("update webhook_deliveries set next_attempt_at = now() + interval '2 minutes' where id = ("
                        " select d.id from webhook_deliveries d join webhook_endpoints e on e.tenant_id = d.tenant_id"
                        " and e.id = d.endpoint_id where d.status = 'pending' and d.next_attempt_at <= now()"
                        " and e.active order by d.next_attempt_at for update of d skip locked limit 1)"
                        " returning id, endpoint_id, event, payload, attempts")
            row = cur.fetchone()
            if row is None:
                break
            cur.execute("select url, secret from webhook_endpoints where id = %s", (row["endpoint_id"],))
            ep = cur.fetchone()
        body = json.dumps(row["payload"], ensure_ascii=False, separators=(",", ":")).encode()
        code, error = _post(ep["url"], ep["secret"], str(row["id"]), row["event"], body)
        attempts = row["attempts"] + 1
        with system_tx() as cur:
            if error is None:
                cur.execute("update webhook_deliveries set status = 'sent', attempts = %s, last_status_code = %s, "
                            "last_error = null, sent_at = now() where id = %s", (attempts, code, row["id"]))
                cur.execute("update webhook_endpoints set last_success_at = now(), last_error = null where id = %s",
                            (row["endpoint_id"],))
            else:
                final = attempts > len(RETRY_DELAYS_S)
                delay = RETRY_DELAYS_S[min(attempts, len(RETRY_DELAYS_S)) - 1]
                cur.execute("update webhook_deliveries set status = %s, attempts = %s, last_status_code = %s, "
                            "last_error = %s, next_attempt_at = now() + make_interval(secs => %s) where id = %s",
                            ("failed" if final else "pending", attempts, code, error[:200], delay, row["id"]))
                cur.execute("update webhook_endpoints set last_error = %s where id = %s", (error[:200], row["endpoint_id"]))
        done += 1
    return done


def send_test(tenant_id: str, endpoint_id: str) -> dict[str, Any]:
    """«Enviar prueba» desde el panel: un evento `ping` firmado, en el momento (sin outbox)."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("select url, secret from webhook_endpoints where tenant_id = %s and id = %s",
                    (tenant_id, endpoint_id))
        row = cur.fetchone()
    if row is None:
        raise LookupError(endpoint_id)
    body = json.dumps({"event": "ping", "created_at": int(time.time()), "data": {}}).encode()
    code, error = _post(row["url"], row["secret"], "ping-" + secrets.token_hex(8), "ping", body)
    return {"ok": error is None, "status_code": code, "error": error}
