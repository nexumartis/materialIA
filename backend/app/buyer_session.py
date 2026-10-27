"""Prueba de pertenencia del comprador en el chat público.

Al crear una conversación desde la tienda pública el servidor emite un token aleatorio y guarda
sólo su SHA-256 (0006_buyer_access.sql). El comprador lo manda en el header `X-Conversation-Token`
(nunca en la URL, el trace ni el historial) en cada lectura y escritura: conocer la UUID no
alcanza. Las conversaciones del sandbox no tienen token y las públicas no se abren desde él.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Optional
from uuid import UUID

from .db import tenant_tx

HEADER = "X-Conversation-Token"


def _digest(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def start(tenant_id: str) -> tuple[str, str]:
    """Conversación nueva de la tienda pública. Devuelve (id, token); el token no se guarda."""
    token = secrets.token_urlsafe(32)
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "insert into conversations (tenant_id, channel, status, access_token_hash) "
            "values (%s, 'web_public', 'open', %s) returning id",
            (tenant_id, _digest(token)),
        )
        return str(cur.fetchone()["id"]), token


def owns(tenant_id: str, conversation_id: str, token: Optional[str]) -> bool:
    """¿El token es el de esta conversación de este negocio?"""
    if not token or not _valid_uuid(conversation_id):
        return False
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select 1 from conversations where tenant_id = %s and id = %s and access_token_hash = %s",
            (tenant_id, conversation_id, _digest(token)),
        )
        return cur.fetchone() is not None


_IN_PUBLIC_THREAD = {
    table: f"select 1 from {table} r join conversations c "
           "on c.tenant_id = r.tenant_id and c.id = r.conversation_id "
           "where r.tenant_id = %s and r.id = %s and c.access_token_hash is not null"
    for table in ("orders", "opportunities")
}


def in_public_thread(table: str, tenant_id: str, record_id: str) -> bool:
    """¿El pedido u oportunidad cuelga de una conversación de comprador? El sandbox no los toca."""
    if not _valid_uuid(record_id):
        return False
    with tenant_tx(tenant_id) as cur:
        cur.execute(_IN_PUBLIC_THREAD[table], (tenant_id, record_id))
        return cur.fetchone() is not None


def is_public(tenant_id: str, conversation_id: str) -> bool:
    """Conversación de un comprador de la tienda pública (el sandbox no la puede usar)."""
    if not _valid_uuid(conversation_id):
        return False
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select 1 from conversations where tenant_id = %s and id = %s and access_token_hash is not null",
            (tenant_id, conversation_id),
        )
        return cur.fetchone() is not None
