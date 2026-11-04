"""Centro de avisos del panel: lo que necesita a alguien del equipo, juntado en un lugar.

Se calcula en vivo del estado real (no hay una tabla de notificaciones que se desincronice):
conversaciones derivadas sin atender, pedidos para revisar, comprobantes por cotejar, turnos nuevos
y clientes insatisfechos. Lo «visto» lo recuerda el navegador de cada persona. Corre en `user_tx`
(RLS por negocio).
"""
from __future__ import annotations

from typing import Any

LIMIT = 40
_ATTENTION = {"amount_mismatch": "el monto pagado no coincide", "duplicate_payment": "cobro duplicado",
              "paid_without_stock": "pagado sin stock", "payment_refunded": "pago devuelto"}


def _item(kind: str, text: str, href: str, at: Any, key: str) -> dict[str, Any]:
    return {"kind": kind, "text": text, "href": href, "at": at.isoformat(), "key": f"{kind}:{key}"}


def list_alerts(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cur.execute("select id, needs_human_at, needs_human_reason from conversations where tenant_id = %s "
                "and channel <> 'eval' and needs_human_at is not null and taken_by is null "
                "order by needs_human_at desc limit %s", (tenant_id, LIMIT))
    reasons = {"asked": "pidió hablar con una persona", "quote": "necesita una cotización",
               "topic": "tocó un tema para el equipo"}
    for r in cur.fetchall():
        out.append(_item("handoff", f"Un cliente {reasons.get(r['needs_human_reason'] or '', 'necesita atención')}",
                         f"#/conversaciones/{r['id']}", r["needs_human_at"], f"{r['id']}:{r['needs_human_at'].isoformat()}"))
    cur.execute("select id, number, attention_reason, updated_at from orders where tenant_id = %s "
                "and attention_reason is not null order by updated_at desc limit %s", (tenant_id, LIMIT))
    for r in cur.fetchall():
        why = _ATTENTION.get(r["attention_reason"], "revisar el cobro")
        out.append(_item("order", f"Pedido #{r['number']}: {why}", "#/pedidos", r["updated_at"],
                         f"{r['id']}:{r['attention_reason']}"))
    cur.execute("select d.id, d.received_at as created_at, o.number from payment_documents d left join orders o "
                "on o.tenant_id = d.tenant_id and o.id = d.order_id where d.tenant_id = %s and d.decision is null "
                "order by d.received_at desc limit %s", (tenant_id, LIMIT))
    for r in cur.fetchall():
        what = f"del pedido #{r['number']}" if r["number"] else "sin pedido"
        out.append(_item("receipt", f"Comprobante {what} para cotejar en tu banco", "#/pedidos", r["created_at"], str(r["id"])))
    cur.execute("select id, service, starts_at, created_at from appointments where tenant_id = %s and status = 'booked' "
                "and starts_at >= now() and created_at >= now() - interval '7 days' order by created_at desc limit %s",
                (tenant_id, LIMIT))
    from .booking import label
    for r in cur.fetchall():
        out.append(_item("appointment", f"Turno nuevo: {r['service']}, {label(r['starts_at'])}", "#/turnos",
                         r["created_at"], str(r["id"])))
    cur.execute("select r.order_id, r.conversation_id, r.score, r.updated_at, o.number from order_ratings r "
                "join orders o on o.tenant_id = r.tenant_id and o.id = r.order_id where r.tenant_id = %s "
                "and r.score <= 2 and r.updated_at >= now() - interval '14 days' order by r.updated_at desc limit %s",
                (tenant_id, LIMIT))
    for r in cur.fetchall():
        href = f"#/conversaciones/{r['conversation_id']}" if r["conversation_id"] else "#/resultados"
        out.append(_item("rating", f"Calificó {r['score']}/5 el pedido #{r['number']}", href, r["updated_at"],
                         f"{r['order_id']}:{r['score']}"))
    out.sort(key=lambda a: a["at"], reverse=True)
    return out[:LIMIT]
