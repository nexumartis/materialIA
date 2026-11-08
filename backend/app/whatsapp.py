"""WhatsApp (Cloud API de Meta): conexión de cada local, avisos firmados, mensajes entrantes y envío.

El negocio de un aviso sale SÓLO del `phone_number_id` registrado en `whatsapp_connections`; nunca
del contenido. El token de cada local se guarda cifrado y no sale en respuestas, logs ni errores.
Diseño: docs/superpowers/specs/2026-11-08-whatsapp-design.md.

    WHATSAPP_CONNECT_TOKEN=... python -m app.whatsapp connect --tenant UUID --phone-number-id ID \\
        --waba-id ID --display-phone "+1 555 165 4354"
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import logging
import os
import sys
import threading
import time
from typing import Any, Optional

import httpx
import psycopg
from cryptography.fernet import Fernet, InvalidToken

from .config import settings
from .db import system_tx, tenant_tx

MAX_TEXT = 4096                       # tope de un mensaje de texto de WhatsApp
UNSUPPORTED_REPLY = "Por ahora entiendo mensajes de texto. ¿Me lo escribís?"
IGNORED_TYPES = frozenset({"reaction", "system", "unsupported"})   # ni se guardan ni se contestan
MAX_INBOUND_ATTEMPTS = 3

log = logging.getLogger("app.whatsapp")
RETRY_DELAYS_S = (30, 120, 600)       # esperas entre reintentos; después del último, 'failed'


class NumberTaken(ValueError):
    def __init__(self):
        super().__init__("Ese número de WhatsApp ya está conectado a otro negocio.")


def enabled() -> bool:
    return bool(settings.whatsapp_app_secret and settings.whatsapp_verify_token and settings.whatsapp_token_key)


def verify_signature(body: bytes, header: Optional[str]) -> bool:
    """`X-Hub-Signature-256` = 'sha256=' + HMAC-SHA256 del cuerpo crudo con el secreto de la app."""
    if not header or not settings.whatsapp_app_secret:
        return False
    expected = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def _fernet() -> Fernet:
    return Fernet(settings.whatsapp_token_key.encode())


def connect(tenant_id: str, phone_number_id: str, waba_id: str, display_phone: str, token: str) -> None:
    """Conecta (o reconecta) el número de un negocio. Un número no puede ser de dos negocios."""
    secret = _fernet().encrypt(token.encode()).decode()
    try:
        with system_tx() as cur:
            cur.execute(
                "insert into whatsapp_connections (tenant_id, phone_number_id, waba_id, display_phone, token_encrypted) "
                "values (%s, %s, %s, %s, %s) on conflict (tenant_id) do update set "
                "phone_number_id = excluded.phone_number_id, waba_id = excluded.waba_id, "
                "display_phone = excluded.display_phone, token_encrypted = excluded.token_encrypted, "
                "status = 'connected', updated_at = now()",
                (tenant_id, phone_number_id, waba_id, display_phone, secret))
    except psycopg.errors.UniqueViolation:
        raise NumberTaken() from None


def tenant_for(phone_number_id: str) -> Optional[str]:
    with system_tx() as cur:
        cur.execute("select tenant_id from whatsapp_connections where phone_number_id = %s and status = 'connected'",
                    (phone_number_id,))
        row = cur.fetchone()
    return str(row["tenant_id"]) if row else None


def _token(tenant_id: str) -> str:
    with system_tx() as cur:
        cur.execute("select token_encrypted from whatsapp_connections where tenant_id = %s", (tenant_id,))
        row = cur.fetchone()
    if row is None:
        raise LookupError("El negocio no tiene WhatsApp conectado.")
    return _fernet().decrypt(row["token_encrypted"].encode()).decode()


# --- Conversaciones ---------------------------------------------------------------------------
def conversation_for(tenant_id: str, wa_id: str) -> str:
    """La conversación de este contacto en este negocio (una sola; se crea la primera vez)."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("insert into conversations (tenant_id, channel, status, wa_id) values (%s, 'whatsapp', 'open', %s) "
                    "on conflict (tenant_id, wa_id) where wa_id is not null do nothing", (tenant_id, wa_id))
        cur.execute("select id from conversations where tenant_id = %s and wa_id = %s", (tenant_id, wa_id))
        return str(cur.fetchone()["id"])


# --- Avisos de Meta -------------------------------------------------------------------------
def process_payload(payload: dict[str, Any]) -> int:
    """Procesa un aviso ya verificado. Devuelve cuántos mensajes nuevos procesó. Un número que no
    está conectado se ignora entero: ni conversación ni IA."""
    done = 0
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            pnid = (value.get("metadata") or {}).get("phone_number_id")
            tenant = tenant_for(str(pnid)) if pnid else None
            if tenant is None:
                continue
            for status in value.get("statuses") or []:
                try:
                    _status(tenant, status)
                except Exception:  # noqa: BLE001 — un aviso que falla no tira los demás
                    log.exception("whatsapp: no pude registrar un estado")
            for message in value.get("messages") or []:
                try:
                    done += _inbound(tenant, message)
                except Exception:  # noqa: BLE001 — queda sin procesar y lo retoma retry_unprocessed
                    log.exception("whatsapp: falló un mensaje entrante")
    return done


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _contact_lock(key: str) -> threading.Lock:
    """Un turno por contacto a la vez: una ráfaga de mensajes no corre turnos en paralelo.
    ponytail: lock en memoria, vale con UN proceso de API; con varios, pg_advisory_xact_lock."""
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _status(tenant_id: str, status: dict[str, Any]) -> None:
    if status.get("status") != "failed" or not status.get("id"):
        return
    err = (status.get("errors") or [{}])[0]
    with system_tx() as cur:
        cur.execute("update whatsapp_outbox set status = 'failed', last_error = %s where tenant_id = %s and wamid = %s",
                    (f"{err.get('code', '')} {err.get('title', '')}".strip()[:200], tenant_id, status["id"]))


def _inbound(tenant_id: str, message: dict[str, Any]) -> int:
    wamid, wa_id = message.get("id"), message.get("from")
    if not wamid or not wa_id or message.get("type") in IGNORED_TYPES:
        return 0
    with system_tx() as cur:      # Meta reintenta: cada mensaje, una sola vez
        cur.execute("insert into whatsapp_inbound (wamid, tenant_id, message) values (%s, %s, %s::jsonb) "
                    "on conflict do nothing", (wamid, tenant_id, json.dumps(message)))
        if cur.rowcount == 0:
            return 0
    _attend(tenant_id, message)
    return 1


def _attend(tenant_id: str, message: dict[str, Any]) -> None:
    """Atiende un mensaje ya registrado y lo marca procesado. Si algo falla antes de marcarlo, queda
    para `retry_unprocessed`. ponytail: si el turno se cortó a la mitad, el reintento puede repetir
    el mensaje entrante en el historial."""
    from .agent import sales_agent
    from .domain import customer_memory, inbox, limits, opportunities, privacy

    wa_id = message["from"]
    with _contact_lock(f"{tenant_id}:{wa_id}"):
        conv = conversation_for(tenant_id, wa_id)
        customer = customer_memory.identify(tenant_id, "whatsapp", f"whatsapp:{wa_id}")
        if customer:
            customer_memory.link_conversation(tenant_id, conv, customer)
        if not privacy.is_blocked(tenant_id, conv) and limits.hit(
                "wa-contact", f"{tenant_id}:{wa_id}", settings.whatsapp_per_contact_hour, 3600):
            if message.get("type") == "text":
                sales_agent.handle_sales_message(tenant_id, (message.get("text") or {}).get("body") or "", conv,
                                                 channel="whatsapp")
            else:
                opportunities.add_message(tenant_id, conv, "inbound", f"[{message.get('type')}]")
                if not inbox.is_taken(tenant_id, conv):      # nunca encima de una persona
                    opportunities.add_message(tenant_id, conv, "outbound", UNSUPPORTED_REPLY)
        with system_tx() as cur:
            cur.execute("update whatsapp_inbound set processed_at = now() where wamid = %s", (message["id"],))
    deliver_due(conversation_id=conv)


def retry_unprocessed(limit: int = 20) -> int:
    """Worker: retoma los mensajes que quedaron sin procesar (falla o reinicio), hasta 3 intentos."""
    done = 0
    while done < limit:
        with system_tx() as cur:
            cur.execute("update whatsapp_inbound set attempts = attempts + 1, received_at = now() where wamid = ("
                        " select wamid from whatsapp_inbound where processed_at is null and message is not null"
                        " and attempts < %s and received_at < now() - interval '2 minutes'"
                        " order by received_at for update skip locked limit 1)"
                        " returning tenant_id, message", (MAX_INBOUND_ATTEMPTS,))
            row = cur.fetchone()
        if row is None:
            break
        done += 1
        try:
            _attend(str(row["tenant_id"]), row["message"])
        except Exception:  # noqa: BLE001
            log.exception("whatsapp: falló el reintento de un mensaje entrante")
    return done


# --- Envío ----------------------------------------------------------------------------------
def split_text(text: str, limit: int = MAX_TEXT) -> list[str]:
    """Partes de hasta `limit` caracteres, cortando en un salto de línea cuando se puede."""
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit + 1)
        if cut <= 0:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


def _client() -> httpx.Client:
    """Frontera HTTP con Meta (los tests la reemplazan por un MockTransport)."""
    return httpx.Client(timeout=15, follow_redirects=False, trust_env=False)


def _body(content: str, payload: Optional[dict[str, Any]]) -> str:
    url = ((payload or {}).get("payment") or {}).get("url")
    return f"{content}\n{url}" if url and url not in content else content


def _post(tenant_id: str, phone_number_id: str, to: str, parts: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Manda las partes en orden. Devuelve (wamid de la última, None) o (None, error sin secretos)."""
    url = f"https://graph.facebook.com/{settings.whatsapp_graph_version}/{phone_number_id}/messages"
    try:
        headers = {"Authorization": f"Bearer {_token(tenant_id)}"}
        wamid = None
        with _client() as client:
            for part in parts:
                r = client.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": to,
                                                            "type": "text", "text": {"body": part}})
                if r.status_code != 200:
                    try:
                        err = r.json().get("error") or {}
                    except ValueError:
                        err = {}
                    return None, f"HTTP {r.status_code}: {err.get('code', '')} {err.get('message', '')}".strip()[:200]
                wamid = (r.json().get("messages") or [{}])[0].get("id")
        return wamid, None
    except (httpx.HTTPError, LookupError, ValueError, InvalidToken) as exc:
        return None, type(exc).__name__


def deliver_due(limit: int = 20, budget_s: float = 20.0, conversation_id: Optional[str] = None) -> int:
    """Manda los mensajes pendientes, de a uno y en orden de creación. Cada fila se RECLAMA corriendo
    su próximo intento 2 minutos (dos procesos no la mandan a la vez) y el POST va fuera de la
    transacción. Fuera de la ventana de 24 h no se manda: queda 'window_closed', sin reintentos.
    ponytail: si falla la 2.ª parte de un texto largo, el reintento repite la 1.ª."""
    started, done = time.monotonic(), 0
    while done < limit and time.monotonic() - started < budget_s:
        with system_tx() as cur:
            cur.execute("update whatsapp_outbox set next_attempt_at = now() + interval '2 minutes' where id = ("
                        " select id from whatsapp_outbox where status = 'pending' and next_attempt_at <= now()"
                        " and (%(conv)s::uuid is null or conversation_id = %(conv)s::uuid)"
                        " order by created_at for update skip locked limit 1)"
                        " returning id, tenant_id, attempts", {"conv": conversation_id})
            row = cur.fetchone()
            if row is None:
                break
            cur.execute("select c.wa_id, c.last_customer_message_at > now() - interval '24 hours' as open, "
                        "m.content, m.payload, w.phone_number_id from whatsapp_outbox o "
                        "join conversations c on c.id = o.conversation_id join messages m on m.id = o.message_id "
                        "left join whatsapp_connections w on w.tenant_id = o.tenant_id and w.status = 'connected' "
                        "where o.id = %s", (row["id"],))
            info = cur.fetchone()
            if not info["open"]:
                skip = ("window_closed", None)
            elif not (info["wa_id"] and info["phone_number_id"]):
                skip = ("failed", "sin WhatsApp conectado o contacto borrado")
            else:
                skip = None
            if skip:
                cur.execute("update whatsapp_outbox set status = %s, last_error = %s where id = %s", (*skip, row["id"]))
        done += 1
        if skip:
            continue
        wamid, error = _post(str(row["tenant_id"]), info["phone_number_id"], info["wa_id"],
                             split_text(_body(info["content"], info["payload"])))
        attempts = row["attempts"] + 1
        with system_tx() as cur:
            if error is None:
                cur.execute("update whatsapp_outbox set status = 'sent', attempts = %s, wamid = %s, last_error = null, "
                            "sent_at = now() where id = %s", (attempts, wamid, row["id"]))
            else:
                final = attempts > len(RETRY_DELAYS_S)
                delay = RETRY_DELAYS_S[min(attempts, len(RETRY_DELAYS_S)) - 1]
                cur.execute("update whatsapp_outbox set status = %s, attempts = %s, last_error = %s, "
                            "next_attempt_at = now() + make_interval(secs => %s) where id = %s",
                            ("failed" if final else "pending", attempts, error, delay, row["id"]))
    return done


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.whatsapp")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("connect", help="Conecta un número de WhatsApp a un negocio (token en WHATSAPP_CONNECT_TOKEN).")
    c.add_argument("--tenant", required=True)
    c.add_argument("--phone-number-id", required=True)
    c.add_argument("--waba-id", required=True)
    c.add_argument("--display-phone", required=True)
    args = parser.parse_args(argv)
    token = os.environ.get("WHATSAPP_CONNECT_TOKEN", "")
    if not token or not settings.whatsapp_token_key:
        sys.exit("Faltan WHATSAPP_CONNECT_TOKEN o WHATSAPP_TOKEN_KEY.")
    connect(args.tenant, args.phone_number_id, args.waba_id, args.display_phone, token)
    print(f"WhatsApp {args.display_phone} conectado al negocio {args.tenant}.")


if __name__ == "__main__":
    main(sys.argv[1:])
