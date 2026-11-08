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
import os
import sys
from typing import Optional

import psycopg
from cryptography.fernet import Fernet

from .config import settings
from .db import system_tx


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
