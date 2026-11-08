"""Datos sensibles y bloqueo de contactos.

- **Tarjetas:** un número de tarjeta que escribe el cliente (13 a 19 dígitos que pasan Luhn) se
  enmascara ANTES de guardarlo o mandarlo a la IA: nunca queda en la base («•••• 1234»).
- **Ocultar datos sensibles:** el equipo tapa DNI, CUIT/CUIL, CBU/CVU y tarjetas de una conversación
  (mensajes, resumen de derivación). Irreversible y auditado.
- **Bloquear:** pausa el agente en la conversación y en las del mismo cliente recordado; el chat
  público responde 403 sin gastar IA. Se puede desbloquear.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..db import tenant_tx
from . import opportunities

_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CBU = re.compile(r"(?<!\d)\d{22}(?!\d)")
_CUIT = re.compile(r"(?<!\d)(?:20|23|24|27|30|33|34)-?\d{8}-?\d(?!\d)")
# DNI: con etiqueta («DNI 30.123.456», «documento: 30123456») o 7-8 dígitos sueltos SIN puntos (un
# monto con puntos como 1.250.000 no se toca).
_DNI = re.compile(r"(?i)(?:dni|documento|doc\.?)\s*(?:n[°ºo]\.?)?\s*:?\s*\d{1,2}\.?\d{3}\.?\d{3}(?!\d)"
                  r"|(?<![\d.,$])\d{7,8}(?![\d.,])")


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total, alt = total + n, not alt
    return total % 10 == 0


def mask_cards(text: str) -> str:
    """Tarjetas -> «•••• 1234» (sólo si pasa Luhn: un CBU o un teléfono no se tocan acá)."""
    def sub(m: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return f"•••• {digits[-4:]}" if 13 <= len(digits) <= 19 and _luhn(digits) else m.group(0)
    return _CARD.sub(sub, text or "")


def redact(text: str) -> str:
    """Todo lo sensible: tarjetas, CBU/CVU, CUIT/CUIL y DNI."""
    text = mask_cards(text)
    text = _CBU.sub("[CBU oculto]", text)
    text = _CUIT.sub("[CUIT oculto]", text)
    return _DNI.sub(lambda m: re.sub(r"\d[\d.]*\d", "[DNI oculto]", m.group(0)), text)


def redact_conversation(cur: Any, tenant_id: str, uid: str, conversation_id: str) -> int:
    """Oculta los datos sensibles de la conversación (mensajes y resumen). Devuelve cuántos mensajes
    cambiaron. LookupError si no es del negocio."""
    cur.execute("select 1 from conversations where tenant_id = %s and id = %s for update", (tenant_id, conversation_id))
    if cur.fetchone() is None:
        raise LookupError(conversation_id)
    cur.execute("select id, content from messages where tenant_id = %s and conversation_id = %s",
                (tenant_id, conversation_id))
    changed = 0
    for m in cur.fetchall():
        clean = redact(m["content"])
        if clean != m["content"]:
            cur.execute("update messages set content = %s where id = %s", (clean, m["id"]))
            changed += 1
    # El resumen se conserva: sólo se tapan los datos sensibles de sus textos.
    cur.execute("select handoff_summary from conversations where tenant_id = %s and id = %s", (tenant_id, conversation_id))
    summary = cur.fetchone()["handoff_summary"]
    if summary:
        clean = {**summary, "quiere": redact(summary.get("quiere") or ""), "falta": redact(summary.get("falta") or ""),
                 "datos": [redact(d) for d in summary.get("datos") or []]}
        if clean != summary:
            cur.execute("update conversations set handoff_summary = %s::jsonb where tenant_id = %s and id = %s",
                        (json.dumps(clean, ensure_ascii=False), tenant_id, conversation_id))
    # La entrega de sus pedidos también tiene datos personales: quedan el método y la localidad.
    cur.execute("update orders set delivery_contact = case when delivery_contact is null then null else "
                "'{\"name\": \"[oculto]\", \"phone\": \"[oculto]\"}'::jsonb end, "
                "delivery_address = case when delivery_address is null then null else jsonb_build_object("
                "'localidad', delivery_address->>'localidad', 'departamento', delivery_address->>'departamento', "
                "'provincia', delivery_address->>'provincia', 'texto', '[dirección oculta], ' || coalesce(delivery_address->>'localidad', '')) end "
                "where tenant_id = %s and conversation_id = %s", (tenant_id, conversation_id))
    # El número de WhatsApp también es un dato personal: si vuelve a escribir, es una conversación nueva.
    cur.execute("update conversations set redacted_at = now(), wa_id = null where tenant_id = %s and id = %s",
                (tenant_id, conversation_id))
    opportunities._audit(cur, tenant_id, "conversation_redacted", conversation_id, {"actor": uid, "messages": changed})
    return changed


def set_blocked(cur: Any, tenant_id: str, uid: str, conversation_id: str, blocked: bool) -> bool:
    """Bloquear marca esta conversación; desbloquear libera TODAS las del mismo cliente recordado
    (si no, otra conversación suya bloqueada lo seguiría frenando)."""
    if blocked:
        cur.execute("update conversations set blocked_at = now(), blocked_by = %s where tenant_id = %s and id = %s",
                    (uid, tenant_id, conversation_id))
    else:
        cur.execute("update conversations set blocked_at = null, blocked_by = null where tenant_id = %s and (id = %s "
                    "or customer_id = (select customer_id from conversations where tenant_id = %s and id = %s))",
                    (tenant_id, conversation_id, tenant_id, conversation_id))
    if not cur.rowcount:
        return False
    opportunities._audit(cur, tenant_id, "conversation_blocked" if blocked else "conversation_unblocked",
                         conversation_id, {"actor": uid})
    return True


def is_blocked(tenant_id: str, conversation_id: str) -> bool:
    """La conversación o el cliente recordado detrás de ella están bloqueados."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("select exists (select 1 from conversations c where c.tenant_id = %(t)s and c.id = %(c)s "
                    "and c.blocked_at is not null) or exists (select 1 from conversations c join conversations o "
                    "on o.tenant_id = c.tenant_id and o.customer_id = c.customer_id and o.blocked_at is not null "
                    "where c.tenant_id = %(t)s and c.id = %(c)s and c.customer_id is not null) as b",
                    {"t": tenant_id, "c": conversation_id})
        return bool(cur.fetchone()["b"])
