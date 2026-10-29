"""Comprobantes de pago de los compradores: recepción, lectura en segundo plano, revisión del
dueño y registro mensual.

Un comprobante es información para que una persona revise. Ni el archivo ni su OCR acreditan un
pago: eso lo hacen el proveedor o el dueño (`payments.service.confirm_transfer`). El texto leído
nunca va a `messages`, al estado del agente ni al LLM.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import time
from datetime import date
from typing import Any, Optional

from psycopg.errors import UniqueViolation

from ..db import system_tx, tenant_tx
from ..domain import receipts
from . import ocr

log = logging.getLogger(__name__)

MIMES = {"jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}
MAX_PER_ORDER = 10
MAX_ATTEMPTS = 3
STALE_CLAIM = "5 minutes"     # un `processing` más viejo se considera caído y se reintenta
AR_TZ = "America/Argentina/Buenos_Aires"


class DuplicateDocument(ValueError):
    """Ese mismo archivo ya se envió para otro pedido del negocio."""


class TooManyDocuments(ValueError):
    """Límite de comprobantes por pedido."""


# --- Comprador ------------------------------------------------------------------
def receive(tenant_id: str, conversation_id: str, order_id: str, data: bytes) -> dict[str, Any]:
    """Guarda el comprobante de un pedido de ESTA conversación. Mismo archivo => mismo registro.

    LookupError si el pedido no es de la conversación; ocr.DocumentRejected si el tipo no sirve."""
    try:
        return _receive(tenant_id, conversation_id, order_id, data)
    except UniqueViolation:
        # Otra subida simultánea del mismo archivo ganó la carrera: ahora se la encuentra
        # (mismo pedido => mismo registro; otro pedido => DuplicateDocument).
        return _receive(tenant_id, conversation_id, order_id, data)


def _receive(tenant_id: str, conversation_id: str, order_id: str, data: bytes) -> dict[str, Any]:
    mime = MIMES[ocr.sniff(data)]
    digest = hashlib.sha256(data).hexdigest()
    with tenant_tx(tenant_id) as cur:
        cur.execute("select status from orders where tenant_id = %s and id = %s and conversation_id = %s "
                    "for update", (tenant_id, order_id, conversation_id))
        order = cur.fetchone()
        if order is None or order["status"] == "CART_OPEN":
            raise LookupError("pedido no encontrado")
        cur.execute("select id, order_id from payment_documents where tenant_id = %s and sha256 = %s",
                    (tenant_id, digest))
        same = cur.fetchone()
        if same:
            if str(same["order_id"]) != order_id:
                raise DuplicateDocument("ese comprobante ya se envió para otro pedido")
            return _buyer_view(cur, tenant_id, str(same["id"]))
        cur.execute("select count(*) as n from payment_documents where tenant_id = %s and order_id = %s",
                    (tenant_id, order_id))
        if cur.fetchone()["n"] >= MAX_PER_ORDER:
            raise TooManyDocuments(f"máximo {MAX_PER_ORDER} comprobantes por pedido")
        cur.execute(
            "insert into payment_documents (tenant_id, order_id, conversation_id, sha256, mime, size, content) "
            "values (%s, %s, %s, %s, %s, %s, %s) returning id",
            (tenant_id, order_id, conversation_id, digest, mime, len(data), data),
        )
        return _buyer_view(cur, tenant_id, str(cur.fetchone()["id"]))


_BUYER_COLUMNS = ("d.id, o.number as order_number, d.status, d.decision, d.ocr->'fields' as fields, "
                  "d.ocr->'needs_review' as needs_review, d.received_at")


def _buyer_row(r: dict[str, Any]) -> dict[str, Any]:
    # Sólo campos sugeridos (con su incertidumbre), sin el texto completo del archivo.
    fields = {k: {"value": f["value"], "candidates": f["candidates"]} for k, f in (r["fields"] or {}).items()}
    return {"id": str(r["id"]), "order_number": r["order_number"], "status": r["status"],
            "decision": r["decision"], "fields": fields, "needs_review": r["needs_review"],
            "received_at": r["received_at"].isoformat()}


def _buyer_view(cur: Any, tenant_id: str, doc_id: str) -> dict[str, Any]:
    cur.execute(f"select {_BUYER_COLUMNS} from payment_documents d join orders o "
                "on o.tenant_id = d.tenant_id and o.id = d.order_id where d.tenant_id = %s and d.id = %s",
                (tenant_id, doc_id))
    return _buyer_row(cur.fetchone())


def for_conversation(tenant_id: str, conversation_id: str) -> list[dict[str, Any]]:
    with tenant_tx(tenant_id) as cur:
        cur.execute(f"select {_BUYER_COLUMNS} from payment_documents d join orders o "
                    "on o.tenant_id = d.tenant_id and o.id = d.order_id "
                    "where d.tenant_id = %s and d.conversation_id = %s order by d.received_at",
                    (tenant_id, conversation_id))
        return [_buyer_row(r) for r in cur.fetchall()]


# --- Lectura en segundo plano (worker) ---------------------------------------------
def process_pending(limit: int = 5, budget_s: float = 20.0) -> int:
    """Lee hasta `limit` comprobantes pendientes. Cada uno se reclama con `skip locked` (varios
    workers no leen el mismo) y el OCR corre fuera de la transacción. Un fallo se reintenta en la
    vuelta siguiente del worker, no en esta. Pasado `budget_s` no reclama más: el resto de las
    tareas del worker (p. ej. liberar reservas vencidas) espera como mucho eso + una lectura."""
    started = time.monotonic()
    with system_tx() as cur:   # reclamos caídos que agotaron intentos: no quedan colgados
        cur.execute("update payment_documents set status = 'unreadable', error = 'no se pudo leer' "
                    f"where status = 'processing' and claimed_at < now() - interval '{STALE_CLAIM}' "
                    "and attempts >= %s", (MAX_ATTEMPTS,))
    seen: list[str] = []
    while len(seen) < limit and (not seen or time.monotonic() - started < budget_s):
        with system_tx() as cur:
            cur.execute(
                "update payment_documents set status = 'processing', attempts = attempts + 1, claimed_at = now() "
                "where id = (select id from payment_documents where attempts < %s and id <> all(%s::uuid[]) "
                f"and (status = 'received' or (status = 'processing' and claimed_at < now() - interval '{STALE_CLAIM}')) "
                "order by received_at for update skip locked limit 1) returning id, tenant_id, content, attempts",
                (MAX_ATTEMPTS, seen),
            )
            job = cur.fetchone()
        if job is None:
            break
        seen.append(str(job["id"]))
        _read(str(job["tenant_id"]), seen[-1], bytes(job["content"]), job["attempts"])
    return len(seen)


def _read(tenant_id: str, doc_id: str, data: bytes, attempts: int) -> None:
    status, result, error = "read", None, None
    try:
        result = ocr.read_document(data)
    except ocr.DocumentRejected as exc:
        status, error = "unreadable", str(exc)
    except ocr.OcrFailed as exc:
        status, error = ("received" if attempts < MAX_ATTEMPTS else "unreadable"), str(exc)
    except Exception:  # noqa: BLE001 - un archivo no frena la cola; no se loguea su contenido
        log.exception("lectura del comprobante %s falló", doc_id)
        status, error = ("received" if attempts < MAX_ATTEMPTS else "unreadable"), "error interno del lector"
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "update payment_documents set status = %s, ocr = coalesce(%s::jsonb, ocr), "
            "pages = coalesce(%s, pages), error = %s, claimed_at = null where tenant_id = %s and id = %s",
            (status, json.dumps(result) if result else None, result and result.get("pages"), error,
             tenant_id, doc_id),
        )


# --- Panel del dueño ------------------------------------------------------------
def _month_bounds(month: str) -> date:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month or ""):
        raise ValueError("mes inválido (AAAA-MM)")
    return date.fromisoformat(month + "-01")


def _in_month(column: str) -> str:
    """Filtro del mes calendario en hora argentina (el parámetro es el primer día del mes)."""
    return (f"{column} >= (%(start)s::date)::timestamp at time zone '{AR_TZ}' and "
            f"{column} < ((%(start)s::date + interval '1 month'))::timestamp at time zone '{AR_TZ}'")


def list_month(cur: Any, tenant_id: str, month: str) -> list[dict[str, Any]]:
    """Comprobantes recibidos en el mes (hora argentina), sin el archivo original."""
    params = {"tenant": tenant_id, "start": _month_bounds(month)}
    cur.execute(
        "select d.id, d.order_id, o.number as order_number, o.total, o.currency, o.status as order_status, "
        "d.mime, d.size, d.pages, d.status, d.error, d.ocr->'fields' as fields, "
        "d.ocr->'needs_review' as needs_review, d.decision, d.decided_at, d.payment_id, d.received_at "
        "from payment_documents d join orders o on o.tenant_id = d.tenant_id and o.id = d.order_id "
        f"where d.tenant_id = %(tenant)s and {_in_month('d.received_at')} order by d.received_at desc",
        params,
    )
    return [{**r, "id": str(r["id"]), "order_id": str(r["order_id"]), "total": float(r["total"]),
             "payment_id": str(r["payment_id"]) if r["payment_id"] else None,
             "decided_at": r["decided_at"].isoformat() if r["decided_at"] else None,
             "received_at": r["received_at"].isoformat()} for r in cur.fetchall()]


def original(cur: Any, tenant_id: str, doc_id: str) -> Optional[tuple[str, bytes]]:
    cur.execute("select mime, content from payment_documents where tenant_id = %s and id = %s",
                (tenant_id, doc_id))
    row = cur.fetchone()
    return (row["mime"], bytes(row["content"])) if row else None


def reject(cur: Any, tenant_id: str, uid: str, doc_id: str) -> bool:
    """El dueño descarta el comprobante. No toca pagos: rechazar un archivo no anula un cobro."""
    cur.execute("update payment_documents set decision = 'rejected', decided_by = %s, decided_at = now() "
                "where tenant_id = %s and id = %s and decision is distinct from 'linked'",
                (uid, tenant_id, doc_id))
    return bool(cur.rowcount)


def link(cur: Any, tenant_id: str, uid: str, order_id: str, payment_id: str, doc_ids: list[str]) -> None:
    """Asocia los comprobantes del pedido al pago que el dueño verificó."""
    if doc_ids:
        cur.execute("update payment_documents set decision = 'linked', payment_id = %s, decided_by = %s, "
                    "decided_at = now() where tenant_id = %s and order_id = %s and id = any(%s::uuid[])",
                    (payment_id, uid, tenant_id, order_id, doc_ids))


# --- Registro mensual (CSV para Excel) ----------------------------------------------
_RISKY = ("=", "+", "-", "@", "\t", "\r")


def _text(value: Any) -> str:
    """Celda de texto no confiable: no se ejecuta como fórmula al abrirla en Excel."""
    s = "" if value is None else str(value)
    return "'" + s if s.startswith(_RISKY) else s


def _money(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def month_csv(cur: Any, tenant_id: str, month: str) -> str:
    """Pagos verificados del mes (una fila por pago, aunque tenga varios comprobantes), devoluciones
    en el mes en que ocurrieron, comprobantes recibidos y totales por moneda. Separador `;` y BOM."""
    params = {"tenant": tenant_id, "start": _month_bounds(month)}
    fmt = f"to_char(%s at time zone '{AR_TZ}', 'YYYY-MM-DD HH24:MI')"
    cur.execute(
        f"select 'pago' as kind, {fmt % 'p.verified_at'} as at, o.number, p.provider, p.provider_payment_id, "
        "p.amount, p.currency, (select count(*) from payment_documents d where d.payment_id = p.id) as docs "
        "from payments p join orders o on o.tenant_id = p.tenant_id and o.id = p.order_id "
        f"where p.tenant_id = %(tenant)s and {_in_month('p.verified_at')} "
        f"union all select 'devolucion', {fmt % 'p.reversed_at'}, o.number, p.provider, p.provider_payment_id, "
        "-p.amount, p.currency, 0 from payments p join orders o on o.tenant_id = p.tenant_id and o.id = p.order_id "
        f"where p.tenant_id = %(tenant)s and p.verified_at is not null and {_in_month('p.reversed_at')} "
        "order by 2", params)
    payments = cur.fetchall()
    cur.execute(
        f"select {fmt % 'd.received_at'} as at, o.number, d.status, d.decision, d.ocr->'fields' as fields "
        "from payment_documents d join orders o on o.tenant_id = d.tenant_id and o.id = d.order_id "
        f"where d.tenant_id = %(tenant)s and {_in_month('d.received_at')} order by d.received_at", params)
    documents = cur.fetchall()

    out = io.StringIO()
    out.write("﻿")
    w = csv.writer(out, delimiter=";", lineterminator="\r\n")
    w.writerow(["tipo", "fecha (hora Argentina)", "pedido", "origen", "referencia", "importe", "moneda",
                "comprobantes", "detalle"])
    totals: dict[str, float] = {}
    for p in payments:
        ref = receipts.payment_reference(p["provider"], p["provider_payment_id"])
        totals[p["currency"]] = totals.get(p["currency"], 0.0) + float(p["amount"])
        w.writerow([p["kind"], p["at"], p["number"], receipts.ORIGINS.get(p["provider"], p["provider"]), _text(ref),
                    _money(float(p["amount"])), p["currency"], p["docs"], ""])
    for d in documents:
        f = {k: (v or {}).get("value") for k, v in (d["fields"] or {}).items()}
        detail = (f"leído: importe {f.get('amount') or '?'} {f.get('currency') or ''}, "
                  f"referencia {f.get('reference') or '?'}" if d["fields"] else "sin leer")
        w.writerow(["comprobante", d["at"], d["number"], "", _text(f.get("reference")), "", "",
                    "", _text(f"{d['status']}/{d['decision'] or 'pendiente'} — {detail}")])
    for currency, total in sorted(totals.items()):
        w.writerow(["total", month, "", "", "", _money(total), currency, "", "pagos verificados menos devoluciones"])
    return out.getvalue()
