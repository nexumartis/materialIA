"""Bandeja de conversaciones del panel y toma de control humana (roadmap etapa 2).

El dueño ve las conversaciones de su negocio, toma el control (el agente se pausa en esa
conversación: `sales_agent.handle_sales_message` no responde ni guarda su respuesta si alguien la
tomó durante el turno), contesta como persona y la devuelve al agente. Las acciones del panel
corren con el cursor de `user_tx` (rol app_user, RLS por membresía).
"""
from __future__ import annotations

from typing import Any, Optional

from ..db import tenant_tx
from ..documents import store as documents
from ..schemas import MAX_HUMAN_REPLY
from . import opportunities, orders

FILTERS = {
    "todas": "true",
    "derivadas": "c.needs_human_at is not null",
    "con_pedido": "exists (select 1 from orders o where o.tenant_id = c.tenant_id "
                  "and o.conversation_id = c.id and o.status <> 'CART_OPEN')",
    "sin_responder": "last.direction = 'inbound'",
    "mias": "c.taken_by = %(uid)s",
}
MAX_MESSAGES = 500
# Lo que el agente dejó pendiente para el mensaje siguiente: tras una toma de control ya no vale
# (un "dale" dirigido a la persona no es aceptar una oferta vieja del agente).
PENDING_TURN_KEYS = ("offer", "handoff", "pending")


class TakenByOther(Exception):
    """Otra persona del negocio tiene el control de la conversación (409)."""


def _flags(row: dict[str, Any], uid: str) -> dict[str, Any]:
    taken_by = row["taken_by"]
    return {
        "needs_human": row["needs_human_at"] is not None,
        "needs_human_reason": row["needs_human_reason"] if row["needs_human_at"] else None,
        "taken": taken_by is not None,
        "taken_by_me": taken_by is not None and str(taken_by) == uid,
    }


def list_conversations(cur: Any, tenant_id: str, uid: str, filter_: str = "todas",
                       limit: int = 100) -> list[dict[str, Any]]:
    """Conversaciones con al menos un mensaje, la de actividad más reciente primero."""
    if filter_ not in FILTERS:
        raise ValueError("filtro inválido")
    cur.execute(
        "select c.id, c.channel, c.created_at, c.needs_human_at, c.needs_human_reason, c.taken_by, "
        "last.direction as last_direction, last.content as last_content, last.created_at as last_at, "
        "(select o.number from orders o where o.tenant_id = c.tenant_id and o.conversation_id = c.id "
        " and o.status <> 'CART_OPEN' order by o.created_at desc limit 1) as last_order "
        "from conversations c join lateral (select m.direction, m.content, m.created_at from messages m "
        " where m.tenant_id = c.tenant_id and m.conversation_id = c.id order by m.created_at desc, m.id desc limit 1) "
        "last on true "
        f"where c.tenant_id = %(tenant)s and c.channel <> 'eval' and {FILTERS[filter_]} "
        "order by last.created_at desc limit %(limit)s",
        {"tenant": tenant_id, "uid": uid, "limit": limit},
    )
    return [{"id": str(r["id"]), "channel": r["channel"], **_flags(r, uid),
             "unanswered": r["last_direction"] == "inbound",
             "last_message": (r["last_content"] or "").strip().replace("\n", " ")[:140],
             "last_at": r["last_at"].isoformat(), "last_order": r["last_order"]} for r in cur.fetchall()]


def _conversation(cur: Any, tenant_id: str, conversation_id: str, lock: bool = False) -> Optional[dict[str, Any]]:
    cur.execute("select id, channel, created_at, needs_human_at, needs_human_reason, taken_by from conversations "
                "where tenant_id = %s and id = %s" + (" for update" if lock else ""), (tenant_id, conversation_id))
    return cur.fetchone()


def detail(cur: Any, tenant_id: str, uid: str, conversation_id: str) -> Optional[dict[str, Any]]:
    conv = _conversation(cur, tenant_id, conversation_id)
    if conv is None:
        return None
    rows = opportunities._conversation_messages(cur, tenant_id, conversation_id, MAX_MESSAGES)
    cart = orders._open_cart_row(cur, tenant_id, conversation_id)
    return {
        "id": str(conv["id"]), "channel": conv["channel"], "created_at": conv["created_at"].isoformat(),
        **_flags(conv, uid),
        "messages": [{"author": "cliente" if m["direction"] == "inbound"
                      else "persona" if (m["payload"] or {}).get("type") == "human" else "agente",
                      "content": m["content"], "at": m["created_at"].isoformat()} for m in rows],
        "cart": orders._view(cur, cart) if cart else None,
        "orders": orders._conversation_orders(cur, tenant_id, conversation_id, limit=20),
        "documents": documents._for_conversation(cur, tenant_id, conversation_id),
    }


def _held_by_other(conv: dict[str, Any], uid: str) -> bool:
    return conv["taken_by"] is not None and str(conv["taken_by"]) != uid


def take(cur: Any, tenant_id: str, uid: str, conversation_id: str) -> bool:
    """Toma el control: desde ahora el agente no responde en esta conversación. Nadie le saca la
    conversación a otra persona que la está atendiendo (TakenByOther)."""
    conv = _conversation(cur, tenant_id, conversation_id, lock=True)
    if conv is None:
        return False
    if _held_by_other(conv, uid):
        raise TakenByOther("la está atendiendo otra persona del negocio")
    if conv["taken_by"] is None:
        cur.execute("update conversations set taken_by = %s, taken_at = now() where tenant_id = %s and id = %s",
                    (uid, tenant_id, conversation_id))
        opportunities._audit(cur, tenant_id, "conversation_taken", conversation_id, {"actor": uid})
    return True


def release(cur: Any, tenant_id: str, uid: str, conversation_id: str) -> bool:
    """Devuelve la conversación al agente: vuelve a responder y deja de figurar como derivada.
    Sólo la devuelve quien la tiene."""
    conv = _conversation(cur, tenant_id, conversation_id, lock=True)
    if conv is None:
        return False
    if _held_by_other(conv, uid):
        raise TakenByOther("la está atendiendo otra persona del negocio")
    cur.execute("update conversations set taken_by = null, taken_at = null, needs_human_at = null, "
                "needs_human_reason = null where tenant_id = %s and id = %s", (tenant_id, conversation_id))
    opportunities._audit(cur, tenant_id, "conversation_released", conversation_id, {"actor": uid})
    return True


def reply(cur: Any, tenant_id: str, uid: str, conversation_id: str, text: str) -> bool:
    """Mensaje de una persona del negocio. Si nadie tenía el control, lo toma (el agente no
    contesta encima de una persona)."""
    text = (text or "").strip()
    if not text or len(text) > MAX_HUMAN_REPLY:
        raise ValueError(f"el mensaje debe tener entre 1 y {MAX_HUMAN_REPLY} caracteres")
    if not take(cur, tenant_id, uid, conversation_id):
        return False
    opportunities._add_message(cur, tenant_id, conversation_id, "outbound", text, {"type": "human"})
    opportunities._audit(cur, tenant_id, "human_reply", conversation_id, {"actor": uid, "chars": len(text)})
    return True


def forget_pending_turn(tenant_id: str, conversation_id: str) -> None:
    """Descarta lo que el agente dejó pendiente (oferta, derivación, compra por confirmar) al tomar o
    devolver la conversación. Lo hace el backend: el panel no accede a `agent_state`."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("update conversations set agent_state = coalesce(agent_state, '{}'::jsonb) - %s::text[] "
                    "where tenant_id = %s and id = %s", (list(PENDING_TURN_KEYS), tenant_id, conversation_id))


def is_taken(tenant_id: str, conversation_id: str) -> bool:
    with tenant_tx(tenant_id) as cur:
        cur.execute("select taken_by from conversations where tenant_id = %s and id = %s",
                    (tenant_id, conversation_id))
        row = cur.fetchone()
    return bool(row and row["taken_by"])
