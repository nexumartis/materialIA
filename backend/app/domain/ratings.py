"""Encuesta de satisfacción (CSAT): el comprador califica un pedido PAGADO de su conversación, de 1
a 5 con un comentario opcional. Nunca bloquea la venta ni cambia el pedido: es información para el
dueño (promedio en Resultados y lista de clientes insatisfechos para contactar)."""
from __future__ import annotations

from typing import Any, Optional

from . import opportunities

RATEABLE = ("PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED")
LOW = 2   # 1 o 2 = insatisfecho: aparece en la lista para contactar
MAX_COMMENT = 500


def rate(cur: Any, tenant_id: str, conversation_id: str, order_id: str, score: Any,
         comment: Optional[str]) -> dict[str, Any]:
    """Guarda (o corrige) la calificación. LookupError si el pedido no es de esa conversación;
    ValueError si todavía no está pagado o los datos no valen. Corre como backend (la conversación
    ya se verificó con el token del comprador)."""
    try:
        score = int(score)
    except (TypeError, ValueError):
        raise ValueError("La calificación va de 1 a 5.") from None
    if not 1 <= score <= 5:
        raise ValueError("La calificación va de 1 a 5.")
    comment = (comment or "").strip()[:MAX_COMMENT] or None
    cur.execute("select status from orders where tenant_id = %s and id = %s and conversation_id = %s",
                (tenant_id, order_id, conversation_id))
    row = cur.fetchone()
    if row is None:
        raise LookupError("pedido inexistente")
    if row["status"] not in RATEABLE:
        raise ValueError("Podés calificar el pedido cuando esté pagado.")
    cur.execute(
        "insert into order_ratings (tenant_id, order_id, conversation_id, score, comment) values (%s, %s, %s, %s, %s) "
        "on conflict (tenant_id, order_id) do update set score = excluded.score, comment = excluded.comment, "
        "updated_at = now()", (tenant_id, order_id, conversation_id, score, comment))
    opportunities._audit(cur, tenant_id, "order_rated", order_id, {"score": score})
    return {"order_id": order_id, "score": score, "comment": comment}


def for_orders(cur: Any, tenant_id: str, order_ids: list[str]) -> dict[str, int]:
    if not order_ids:
        return {}
    cur.execute("select order_id, score from order_ratings where tenant_id = %s and order_id = any(%s::uuid[])",
                (tenant_id, order_ids))
    return {str(r["order_id"]): r["score"] for r in cur.fetchall()}


def summary(cur: Any, tenant_id: str, days: int) -> dict[str, Any]:
    """Promedio, distribución y los insatisfechos del período (más recientes primero)."""
    cur.execute("select score, count(*) as n from order_ratings where tenant_id = %s "
                "and updated_at >= now() - make_interval(days => %s) group by score", (tenant_id, days))
    dist = {int(r["score"]): r["n"] for r in cur.fetchall()}
    total = sum(dist.values())
    cur.execute(
        "select r.order_id, r.conversation_id, r.score, r.comment, r.updated_at, o.number, o.total "
        "from order_ratings r join orders o on o.tenant_id = r.tenant_id and o.id = r.order_id "
        "where r.tenant_id = %s and r.score <= %s and r.updated_at >= now() - make_interval(days => %s) "
        "order by r.updated_at desc limit 20", (tenant_id, LOW, days))
    unhappy = [{"order_id": str(r["order_id"]), "order_number": r["number"],
                "conversation_id": str(r["conversation_id"]) if r["conversation_id"] else None,
                "score": r["score"], "comment": r["comment"], "total": float(r["total"]),
                "at": r["updated_at"].isoformat()} for r in cur.fetchall()]
    return {"count": total, "average": round(sum(s * n for s, n in dist.items()) / total, 2) if total else None,
            "distribution": {str(s): dist.get(s, 0) for s in range(1, 6)},
            "satisfied_rate": round((dist.get(4, 0) + dist.get(5, 0)) / total, 4) if total else None,
            "unhappy": unhappy}
