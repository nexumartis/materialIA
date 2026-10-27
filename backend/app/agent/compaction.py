"""Compactación de conversaciones largas (en segundo plano).

El agente ve los últimos HISTORY mensajes completos. Cuando una conversación supera COMPACT_AFTER
mensajes, el worker resume la parte que quedó fuera de esa ventana en `conversations.summary`, y el
agente la recibe como contexto orientativo. El resumen nunca lleva precios ni stock: esos datos
siempre se consultan con herramientas.
"""
from __future__ import annotations

import re
from typing import Any

from ..config import settings
from ..db import system_tx, tenant_tx
from . import llm_tasks

HISTORY = 16
SUMMARY_CHARS = 900
_MONEY = re.compile(r"\$\s?\d[\d.,]*")
# Teléfonos, alturas de calle, documentos (aunque vengan con espacios o guiones) y emails.
_PERSONAL = re.compile(r"\d(?:[\s.\-]?\d){2,}|\S+@\S+")

_PROMPT = """Resumís la parte anterior de una conversación de venta para que el vendedor no pierda
el hilo. Devolvé JSON {"summary": "..."} de hasta 6 oraciones: qué busca el cliente, para qué,
preferencias, productos que le interesaron o descartó (por nombre), decisiones y temas pendientes.
Fusioná con el resumen previo. PROHIBIDO: precios, montos, cantidades en stock, datos de pago o de
contacto."""


def _clean(text: str) -> str:
    text = _PERSONAL.sub("[dato]", _MONEY.sub("[precio]", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:SUMMARY_CHARS]


def compact(tenant_id: str, conversation_id: str, model: Any = None) -> str | None:
    with tenant_tx(tenant_id) as cur:
        # Reclamo con lock consultivo: con varios workers uno solo resume (y paga el modelo), sin
        # bloquear la fila de la conversación que el agente actualiza mientras responde.
        cur.execute("select pg_try_advisory_xact_lock(hashtext(%s)) as ok", (f"compact:{conversation_id}",))
        if not cur.fetchone()["ok"]:
            return None
        cur.execute("select summary, summary_until from conversations where tenant_id = %s and id = %s",
                    (tenant_id, conversation_id))
        conv = cur.fetchone()
        if conv is None:
            return None
        return _compact_locked(cur, tenant_id, conversation_id, conv, model)


def _compact_locked(cur: Any, tenant_id: str, conversation_id: str, conv: dict[str, Any],
                    model: Any) -> str | None:
    cur.execute("select direction, content, created_at from messages "
                "where tenant_id = %s and conversation_id = %s order by created_at, id",
                (tenant_id, conversation_id))
    msgs = cur.fetchall()
    older = msgs[:-HISTORY] if len(msgs) > HISTORY else []
    since = conv["summary_until"] if conv else None
    new = [m for m in older if since is None or m["created_at"] > since]
    if not new:
        return conv["summary"] if conv else None
    transcript = "\n".join(("Cliente: " if m["direction"] == "inbound" else "Vendedor: ") + m["content"][:300]
                           for m in new)
    data = llm_tasks.ask_json(_PROMPT, f"Resumen previo: {conv['summary'] or '(ninguno)'}\n\n"
                                       f"Mensajes a resumir:\n{transcript}", model)
    if data and data.get("summary"):
        summary = _clean(str(data["summary"]))
    else:   # sin modelo: lo que pidió el cliente, en orden
        asked = "; ".join(_clean(m["content"])[:80] for m in new if m["direction"] == "inbound")
        summary = _clean(((conv["summary"] or "") + " Antes el cliente escribió: " + asked).strip())
    cur.execute("update conversations set summary = %s, summary_until = %s where tenant_id = %s and id = %s",
                (summary, new[-1]["created_at"], tenant_id, conversation_id))
    return summary


def compact_due(limit: int = 20, model: Any = None) -> int:
    """Worker: conversaciones con más de COMPACT_AFTER mensajes y parte vieja sin resumir."""
    with system_tx() as cur:
        cur.execute(
            "select c.tenant_id, c.id from conversations c join messages m "
            "on m.tenant_id = c.tenant_id and m.conversation_id = c.id "
            "where c.last_customer_message_at > now() - interval '7 days' "
            "group by c.tenant_id, c.id, c.summary_until "
            "having count(*) > %s and (c.summary_until is null or "
            "count(*) filter (where m.created_at > c.summary_until) > %s) limit %s",
            (settings.compact_after_messages, HISTORY, limit))
        due = cur.fetchall()
    for r in due:
        compact(str(r["tenant_id"]), str(r["id"]), model)
    return len(due)
