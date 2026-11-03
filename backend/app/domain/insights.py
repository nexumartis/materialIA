"""Resultados del agente para el dueño (sirve para cualquier rubro): embudo de conversaciones a
ventas, plata cobrada, cuánto resolvió el agente solo, ventas fuera de horario y productos más
vendidos. Todo sale de datos reales (conversaciones, pedidos y pagos verificados); las
conversaciones de prueba del asistente (`eval`) no cuentan.

Corre en `user_tx` (RLS por negocio). Horario «fuera de hora»: antes de las 9, desde las 19 o fin de
semana, hora Argentina (decisión de Claude: horario comercial típico; no usa el texto libre de
horarios del perfil).
"""
from __future__ import annotations

from typing import Any

from . import ai_usage, ratings

PAID = ("PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED")
_TZ = "America/Argentina/Buenos_Aires"
_OFF_HOURS = (f"(extract(isodow from {{col}} at time zone '{_TZ}') >= 6 "
              f"or extract(hour from {{col}} at time zone '{_TZ}') < 9 "
              f"or extract(hour from {{col}} at time zone '{_TZ}') >= 19)")


def summary(cur: Any, tenant_id: str, days: int = 30) -> dict[str, Any]:
    p = {"t": tenant_id, "days": days, "paid": list(PAID)}
    since = "now() - make_interval(days => %(days)s)"
    # Conversaciones reales del período (con al menos un mensaje del cliente) y hasta dónde llegó cada una.
    cur.execute(f"""
        with conv as (
            select c.id, c.created_at, c.taken_by, c.needs_human_at,
                   exists (select 1 from messages m where m.tenant_id = c.tenant_id and m.conversation_id = c.id
                           and m.direction = 'outbound' and m.payload->>'type' in ('human', 'quote')) as human,
                   exists (select 1 from orders o join order_items i on i.tenant_id = o.tenant_id and i.order_id = o.id
                           where o.tenant_id = c.tenant_id and o.conversation_id = c.id) as cart,
                   exists (select 1 from orders o where o.tenant_id = c.tenant_id and o.conversation_id = c.id
                           and o.status <> 'CART_OPEN') as ordered,
                   exists (select 1 from orders o where o.tenant_id = c.tenant_id and o.conversation_id = c.id
                           and o.status = any(%(paid)s)) as paid
            from conversations c
            where c.tenant_id = %(t)s and c.channel <> 'eval' and c.created_at >= {since}
              and exists (select 1 from messages m where m.tenant_id = c.tenant_id and m.conversation_id = c.id
                          and m.direction = 'inbound'))
        select count(*) as conversations,
               count(*) filter (where cart) as with_cart,
               count(*) filter (where ordered) as with_order,
               count(*) filter (where paid) as with_payment,
               count(*) filter (where not human and taken_by is null and needs_human_at is null) as solo_agent,
               count(*) filter (where needs_human_at is not null and taken_by is null) as waiting_human,
               count(*) filter (where {_OFF_HOURS.format(col='created_at')}) as off_hours
        from conv""", p)
    funnel = cur.fetchone()

    # Ventas cobradas en el período (pago verificado; las reintegradas no cuentan).
    cur.execute(f"""
        select count(*) as orders, coalesce(sum(total), 0) as revenue,
               count(*) filter (where {_OFF_HOURS.format(col='o.created_at')}) as off_orders,
               coalesce(sum(total) filter (where {_OFF_HOURS.format(col='o.created_at')}), 0) as off_revenue
        from orders o where o.tenant_id = %(t)s and o.status = any(%(paid)s) and o.paid_at >= {since}""", p)
    sales = cur.fetchone()

    cur.execute(f"""
        select coalesce(sum(deposit), 0) as deposits, count(*) as n from orders
        where tenant_id = %(t)s and status = 'DEPOSIT_PAID' and deposit_paid_at >= {since}""", p)
    deposits = cur.fetchone()

    cur.execute(f"""
        select g::date as day,
               (select count(*) from conversations c where c.tenant_id = %(t)s and c.channel <> 'eval'
                and (c.created_at at time zone '{_TZ}')::date = g::date
                and exists (select 1 from messages m where m.tenant_id = c.tenant_id and m.conversation_id = c.id
                            and m.direction = 'inbound')) as conversations,
               (select coalesce(sum(total), 0) from orders o where o.tenant_id = %(t)s and o.status = any(%(paid)s)
                and (o.paid_at at time zone '{_TZ}')::date = g::date) as revenue
        from generate_series((now() at time zone '{_TZ}')::date - (%(days)s - 1),
                             (now() at time zone '{_TZ}')::date, interval '1 day') as g
        order by day""", p)
    series = [{"day": r["day"].isoformat(), "conversations": r["conversations"], "revenue": float(r["revenue"])}
              for r in cur.fetchall()]

    cur.execute(f"""
        select i.name, sum(i.qty) as qty, sum(i.line_total) as revenue
        from orders o join order_items i on i.tenant_id = o.tenant_id and i.order_id = o.id
        where o.tenant_id = %(t)s and o.status = any(%(paid)s) and o.paid_at >= {since}
        group by i.name order by revenue desc, qty desc limit 5""", p)
    top = [{"name": r["name"], "qty": int(r["qty"]), "revenue": float(r["revenue"])} for r in cur.fetchall()]

    n = funnel["conversations"]
    revenue, orders_n = float(sales["revenue"]), sales["orders"]
    ai = ai_usage.summary(cur, tenant_id, days)
    return {
        "days": days,
        "funnel": {"conversations": n, "with_cart": funnel["with_cart"], "with_order": funnel["with_order"],
                   "with_payment": funnel["with_payment"]},
        "conversion": round(funnel["with_payment"] / n, 4) if n else None,
        "solo_agent": funnel["solo_agent"],
        "solo_agent_rate": round(funnel["solo_agent"] / n, 4) if n else None,
        "waiting_human": funnel["waiting_human"],
        "off_hours_conversations": funnel["off_hours"],
        "sales": {"orders": orders_n, "revenue": revenue,
                  "average_ticket": round(revenue / orders_n, 2) if orders_n else None,
                  "off_hours_orders": sales["off_orders"], "off_hours_revenue": float(sales["off_revenue"])},
        "deposits": {"orders": deposits["n"], "amount": float(deposits["deposits"])},
        "series": series,
        "top_products": top,
        "ai": {"calls": ai["calls"], "cost": ai["cost"], "currency": ai["currency"]},
        "satisfaction": ratings.summary(cur, tenant_id, days),
        "inbox": inbox_metrics(cur, tenant_id, days),
    }


def inbox_metrics(cur: Any, tenant_id: str, days: int) -> dict[str, Any]:
    """Derivaciones del período: cuántas, por qué, cuántas respondió el equipo y en cuánto tiempo
    (mediana y percentil 90, en minutos), y cuántas siguen sin respuesta ahora."""
    cur.execute(
        "select count(*) as total, count(answered_at) as answered, "
        "percentile_cont(0.5) within group (order by extract(epoch from answered_at - created_at)) "
        "  filter (where answered_at is not null) as p50, "
        "percentile_cont(0.9) within group (order by extract(epoch from answered_at - created_at)) "
        "  filter (where answered_at is not null) as p90 "
        "from handoff_events where tenant_id = %s and created_at >= now() - make_interval(days => %s)",
        (tenant_id, days))
    r = cur.fetchone()
    cur.execute("select reason, count(*) as n from handoff_events where tenant_id = %s "
                "and created_at >= now() - make_interval(days => %s) group by reason order by n desc", (tenant_id, days))
    by_reason = {x["reason"]: x["n"] for x in cur.fetchall()}
    # «Esperando ahora» = lo que la bandeja muestra como derivado y sin nadie que lo tome (el estado
    # actual de la conversación, no eventos viejos que se cerraron sin respuesta escrita).
    cur.execute("select count(*) as n from conversations where tenant_id = %s and channel <> 'eval' "
                "and needs_human_at is not null and taken_by is null", (tenant_id,))
    waiting = cur.fetchone()["n"]
    minutes = lambda s: round(float(s) / 60, 1) if s is not None else None
    return {"handoffs": r["total"], "answered": r["answered"], "waiting_now": waiting, "by_reason": by_reason,
            "first_response_minutes_p50": minutes(r["p50"]), "first_response_minutes_p90": minutes(r["p90"])}
