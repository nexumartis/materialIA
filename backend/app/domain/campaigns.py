"""Campañas: el dueño le escribe a un grupo de clientes según lo que hicieron.

- **Audiencias:** un catálogo cerrado (`AUDIENCES`): carrito abandonado, pagos pendientes (cobranzas),
  compraron, consultaron y no compraron, compraron y no volvieron. Cada una es SQL parametrizado y
  filtrado por negocio; el cliente/LLM nunca manda SQL ni filtros libres. Agregar una audiencia es
  sumar una entrada al catálogo.
- **Destinatario = una charla** (la más reciente de cada cliente): es lo que hoy identifica a un
  comprador. Nunca se escribe a quien se dio de baja, a una charla bloqueada ni a quien ya recibió una
  campaña en los últimos `FREQUENCY_DAYS` días.
- **Mensaje honesto:** `{nombre}`, `{producto}`, `{monto}`, `{negocio}` y `{link}` salen de la base
  (el pedido real, el catálogo, el perfil); no se inventa ningún precio ni dato.
- **Congelado al lanzar:** el worker materializa los destinatarios cuando llega la hora y después los
  envía por el canal, en tandas y con tiempo acotado (`dispatch_due`). Re-chequea la baja al enviar.
- **Canales:** en esta fase sólo `simulado` (queda registrado qué se mandaría; no sale nada del
  sistema). WhatsApp/email se enchufan en `_CHANNELS` cuando se habiliten los envíos a clientes.
- **Resultados:** «compró» = un pedido pagado de esa charla o de ese cliente dentro de
  `ATTRIBUTION_DAYS` después del envío. Se calcula al leer, no se guarda.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from ..config import settings
from ..db import system_tx, tenant_tx
from . import opportunities

log = logging.getLogger(__name__)

PAID = ["PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"]
FREQUENCY_DAYS = 7
ATTRIBUTION_DAYS = 7
MAX_RECIPIENTS = 2000
MAX_LAUNCHES_PER_DAY = 10
PREVIEW_SAMPLE = 5
SEND_BATCH = 200
WORKER_BUDGET_S = 20.0
_AR = ZoneInfo("America/Argentina/Buenos_Aires")
PLACEHOLDERS = ("nombre", "producto", "monto", "negocio", "link")
STATUS_LABELS = {"draft": "Borrador", "scheduled": "Programada", "sending": "Enviando", "sent": "Enviada",
                 "cancelled": "Cancelada"}


# --- Audiencias -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Param:
    name: str
    label: str
    type: str                       # days | amount | text
    default: Any
    minimum: float = 0
    maximum: float = 3650


@dataclass(frozen=True)
class Audience:
    kind: str
    label: str
    description: str
    sql: str                        # devuelve conversation_id, customer_id, order_id, amount, at
    params: tuple[Param, ...] = field(default_factory=tuple)


_DUE = ("case when o.deposit is not null and o.status = 'PENDING_PAYMENT' then o.deposit "
        "when o.deposit is not null and o.status = 'DEPOSIT_PAID' then o.total - o.deposit else o.total end")
_CART_NOW = (
    "(select case when count(*) > 0 and bool_and(ci.active and ci.pricing_mode = 'fixed' and pp.amount is not null) "
    "then sum(i.qty * pp.amount) end from order_items i join catalog_items ci on ci.tenant_id = i.tenant_id "
    "and ci.id = i.item_id left join lateral (select pe.amount from price_entries pe where pe.tenant_id = ci.tenant_id "
    "and pe.item_id = ci.id and pe.valid_from <= current_date and (pe.valid_until is null or pe.valid_until >= current_date) "
    "order by pe.valid_from desc limit 1) pp on true where i.tenant_id = o.tenant_id and i.order_id = o.id)")
_JOIN = "join conversations c on c.tenant_id = o.tenant_id and c.id = o.conversation_id"

AUDIENCES: dict[str, Audience] = {a.kind: a for a in (
    Audience(
        "abandoned_cart", "Carrito abandonado",
        "Armaron un carrito y no lo pagaron. Ideal para recordarles lo que les quedó.",
        # El monto es a precio de HOY (el checkout recotiza): si algún ítem no tiene precio vigente,
        # el carrito no entra (lo atiende una persona, no una campaña).
        f"select * from (select o.conversation_id, c.customer_id, o.id as order_id, {_CART_NOW} as amount, "
        f"o.updated_at as at from orders o {_JOIN} where o.tenant_id = %(t)s and not o.quote "
        f"and o.status = 'CART_OPEN' and o.updated_at <= now() - make_interval(days => %(days)s) "
        f"and o.updated_at >= now() - interval '30 days' "
        f"and not exists (select 1 from orders p where p.tenant_id = o.tenant_id "
        f"and p.conversation_id = o.conversation_id and p.status = any(%(paid)s) and p.created_at >= o.created_at)) cart "
        f"where cart.amount > 0 and cart.amount >= %(min_amount)s",
        (Param("days", "Hace al menos (días)", "days", 3, 1, 30), Param("min_amount", "Monto mínimo", "amount", 20000))),
    Audience(
        "payment_pending", "Pagos pendientes",
        "Cobranzas: pedidos confirmados que esperan el pago, o señas con saldo por pagar.",
        f"select o.conversation_id, c.customer_id, o.id as order_id, {_DUE} as amount, o.updated_at as at "
        f"from orders o {_JOIN} where o.tenant_id = %(t)s and o.status in ('PENDING_PAYMENT', 'DEPOSIT_PAID') "
        f"and o.updated_at <= now() - make_interval(days => %(days)s) and {_DUE} >= %(min_amount)s",
        (Param("days", "Pendiente hace al menos (días)", "days", 2, 0, 365), Param("min_amount", "Monto mínimo", "amount", 0))),
    Audience(
        "bought", "Compraron",
        "Clientes que pagaron una compra (de un producto, si lo indicás) en el período.",
        f"select o.conversation_id, c.customer_id, o.id as order_id, o.total as amount, o.paid_at as at "
        f"from orders o {_JOIN} where o.tenant_id = %(t)s and o.status = any(%(paid)s) "
        f"and o.paid_at >= now() - make_interval(days => %(days)s) "
        f"and (%(product)s = '' or exists (select 1 from order_items i where i.tenant_id = o.tenant_id "
        f"and i.order_id = o.id and i.name ilike '%%' || %(product)s || '%%'))",
        (Param("product", "Producto (opcional)", "text", ""), Param("days", "En los últimos (días)", "days", 90, 1, 730))),
    Audience(
        "not_bought", "Consultaron y no compraron",
        "Escribieron en el período pero nunca pagaron un pedido.",
        "select c.id as conversation_id, c.customer_id, null::uuid as order_id, null::numeric as amount, "
        "c.last_customer_message_at as at from conversations c where c.tenant_id = %(t)s "
        "and c.last_customer_message_at >= now() - make_interval(days => %(days)s) "
        "and c.last_customer_message_at <= now() - interval '1 day' "
        "and not exists (select 1 from orders p join conversations pc on pc.tenant_id = p.tenant_id "
        "and pc.id = p.conversation_id where p.tenant_id = c.tenant_id and p.status = any(%(paid)s) "
        "and (pc.id = c.id or (c.customer_id is not null and pc.customer_id = c.customer_id)))",
        (Param("days", "En los últimos (días)", "days", 30, 2, 365),)),
    Audience(
        "inactive", "Compraron y no volvieron",
        "Clientes con una compra pagada pero ninguna desde hace un tiempo.",
        f"select * from (select distinct on (c.customer_id) o.conversation_id, c.customer_id, o.id as order_id, "
        f"o.total as amount, o.paid_at as at from orders o {_JOIN} where o.tenant_id = %(t)s "
        f"and o.status = any(%(paid)s) and c.customer_id is not null order by c.customer_id, o.paid_at desc) last "
        f"where last.at <= now() - make_interval(days => %(days)s)",
        (Param("days", "Sin comprar hace (días)", "days", 60, 7, 730),)),
)}


def catalog() -> list[dict[str, Any]]:
    return [{"kind": a.kind, "label": a.label, "description": a.description,
             "params": [{"name": p.name, "label": p.label, "type": p.type, "default": p.default} for p in a.params]}
            for a in AUDIENCES.values()]


def clean_audience(raw: Any) -> dict[str, Any]:
    """Valida contra el catálogo: sólo tipos y parámetros conocidos, con rangos. Lo demás se descarta."""
    if not isinstance(raw, dict) or raw.get("kind") not in AUDIENCES:
        raise ValueError("Elegí una audiencia válida.")
    aud = AUDIENCES[raw["kind"]]
    given = raw.get("params") if isinstance(raw.get("params"), dict) else {}
    params: dict[str, Any] = {}
    for p in aud.params:
        v = given.get(p.name, p.default)
        if p.type == "text":
            params[p.name] = re.sub(r"[%_\\]", "", str(v or "")).strip()[:60]
            continue
        try:
            n = float(v if v not in (None, "") else p.default)
        except (TypeError, ValueError):
            raise ValueError(f"«{p.label}» tiene que ser un número.") from None
        if not p.minimum <= n <= (p.maximum if p.type == "days" else 1e9):
            raise ValueError(f"«{p.label}» está fuera de rango.")
        params[p.name] = int(n) if p.type == "days" else round(n, 2)
    return {"kind": aud.kind, "params": params}


def _rows(cur: Any, tenant_id: str, audience: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    """Audiencia resuelta: una fila por cliente (su charla más reciente), con nombre, detalle y si
    queda excluida (baja o contactado hace poco)."""
    aud = AUDIENCES[audience["kind"]]
    args = {"t": tenant_id, "paid": PAID, "freq": FREQUENCY_DAYS, "limit": limit, "days": 0, "min_amount": 0,
            "product": "", **audience["params"]}
    cur.execute(
        f"with base as ({aud.sql}), "
        "one as (select distinct on (coalesce(customer_id, conversation_id)) * from base "
        "        order by coalesce(customer_id, conversation_id), at desc) "
        "select one.conversation_id, one.customer_id, one.order_id, one.amount, one.at, o.number, "
        " coalesce(nullif((select oc.delivery_contact->>'name' from orders oc where oc.tenant_id = %(t)s "
        "   and oc.conversation_id = one.conversation_id and oc.delivery_contact ? 'name' "
        "   order by oc.updated_at desc limit 1), ''), dc.display_name) as name, "
        " (select i.name from order_items i where i.tenant_id = %(t)s and i.order_id = one.order_id "
        "   and (%(product)s = '' or i.name ilike '%%' || %(product)s || '%%') order by i.line_total desc limit 1) as product, "
        " (select count(*) from order_items i where i.tenant_id = %(t)s and i.order_id = one.order_id) as lines, "
        " (dc.opt_out_at is not null or coalesce(dc.consent_status, '') in ('opted_out', 'denied') "
        "   or c.blocked_at is not null or c.marketing_opt_out_at is not null) as opted_out, "
        " exists (select 1 from campaign_recipients r where r.tenant_id = %(t)s and r.status = 'sent' "
        "   and r.sent_at > now() - make_interval(days => %(freq)s) and (r.conversation_id = one.conversation_id "
        "   or (one.customer_id is not null and r.customer_id = one.customer_id))) as recent "
        "from one join conversations c on c.tenant_id = %(t)s and c.id = one.conversation_id "
        "left join demo_customers dc on dc.tenant_id = %(t)s and dc.id = one.customer_id "
        "left join orders o on o.tenant_id = %(t)s and o.id = one.order_id "
        "order by one.at desc limit %(limit)s", args)
    return cur.fetchall()


# --- Mensaje --------------------------------------------------------------------------------
def money(n: Any) -> str:
    return "$" + f"{round(float(n)):,}".replace(",", ".")


def _first_name(name: Optional[str]) -> str:
    """Nombre de pila sólo si es de una persona (no el «Cliente web» genérico)."""
    name = (name or "").strip()
    if not name or name.lower().startswith("cliente"):
        return ""
    return name.split()[0][:30]


def _store(cur: Any, tenant_id: str) -> dict[str, str]:
    cur.execute("select t.name, p.public_slug from tenants t left join agent_profiles p on p.tenant_id = t.id "
                "where t.id = %s", (tenant_id,))
    row = cur.fetchone() or {}
    slug = row.get("public_slug")
    return {"negocio": (row.get("name") or "").split(" (")[0],
            "link": f"{settings.public_web_url.rstrip('/')}/#/tienda/{slug}" if slug else ""}


def _product(row: dict[str, Any]) -> str:
    if not row.get("product"):
        return ""
    extra = int(row.get("lines") or 0) - 1
    return row["product"] + (f" y {extra} más" if extra > 0 else "")


def render(template: str, row: dict[str, Any], store: dict[str, str]) -> str:
    values = {"nombre": _first_name(row.get("name")), "producto": _product(row) or "tu pedido",
              "monto": money(row["amount"]) if row.get("amount") is not None else "", **store}
    text = re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), template)
    text = re.sub(r"[ \t]+([!?.,;:])", r"\1", text)          # «Hola !» -> «Hola!» si no hay nombre
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _detail(kind: str, row: dict[str, Any]) -> str:
    when = row["at"].astimezone(_AR).strftime("%d/%m") if row.get("at") else ""
    amount = money(row["amount"]) if row.get("amount") is not None else ""
    num = f" · pedido #{row['number']}" if row.get("number") else ""
    return {"abandoned_cart": f"Carrito de {amount} · {when}",
            "payment_pending": f"Debe {amount}{num}",
            "bought": f"Compró {_product(row) or 'un pedido'} · {when}",
            "not_bought": f"Consultó el {when}",
            "inactive": f"Última compra {when}"}.get(kind, "")


def _clean_message(message: Any) -> str:
    text = str(message or "").strip()
    if not 1 <= len(text) <= 700:
        raise ValueError("El mensaje tiene que tener entre 1 y 700 caracteres.")
    unknown = {m for m in re.findall(r"\{(\w+)\}", text) if m not in PLACEHOLDERS}
    if unknown:
        raise ValueError("No conozco " + ", ".join(sorted("{" + u + "}" for u in unknown)) + ".")
    return text


# --- Panel ----------------------------------------------------------------------------------
def channel_info() -> dict[str, Any]:
    return {"name": _enabled_channels()[0], "real_sending": any(c != "simulado" for c in _enabled_channels()),
            "note": "En esta etapa los envíos son simulados: queda registrado a quién y qué se mandaría, "
                    "pero no le llega nada a nadie. Cuando se habilite WhatsApp, las campañas salen por ahí."}


def _enabled_channels() -> list[str]:
    return [c for c in (x.strip() for x in settings.campaign_channels.split(",")) if c in _CHANNELS] or ["simulado"]


def preview(cur: Any, tenant_id: str, audience: Any, message: Any) -> dict[str, Any]:
    audience = clean_audience(audience)
    template = _clean_message(message) if str(message or "").strip() else ""
    rows = _rows(cur, tenant_id, audience, MAX_RECIPIENTS * 2)
    ok = [r for r in rows if not r["opted_out"] and not r["recent"]]
    store = _store(cur, tenant_id)
    return {"count": min(len(ok), MAX_RECIPIENTS),
            "excluded": {"opted_out": sum(1 for r in rows if r["opted_out"]),
                         "recently_contacted": sum(1 for r in rows if r["recent"] and not r["opted_out"])},
            "sample": [{"name": r["name"] or "Cliente", "detail": _detail(audience["kind"], r),
                        "message": render(template, r, store) if template else ""} for r in ok[:PREVIEW_SAMPLE]]}


_SUMMARY = (
    "select c.id, c.name, c.audience, c.channel, c.status, c.scheduled_at, c.created_at, c.sent_at, "
    " count(r.id) as recipients, count(r.id) filter (where r.status = 'sent') as sent, "
    " count(r.id) filter (where r.status = 'skipped') as skipped, count(r.id) filter (where r.status = 'failed') as failed, "
    " count(conv.order_id) as converted, coalesce(sum(conv.total), 0) as revenue "
    "from campaigns c left join campaign_recipients r on r.tenant_id = c.tenant_id and r.campaign_id = c.id "
    "left join lateral (select o.id as order_id, o.total from orders o join conversations oc on oc.tenant_id = o.tenant_id "
    " and oc.id = o.conversation_id where r.status = 'sent' and o.tenant_id = c.tenant_id and o.status = any(%(paid)s) "
    " and o.paid_at > r.sent_at and o.paid_at <= r.sent_at + make_interval(days => %(attr)s) "
    " and (oc.id = r.conversation_id or (r.customer_id is not null and oc.customer_id = r.customer_id)) "
    " order by o.paid_at limit 1) conv on true "
    "where c.tenant_id = %(t)s {where} group by c.id order by c.created_at desc limit 100")


def _summary(row: dict[str, Any]) -> dict[str, Any]:
    aud = AUDIENCES.get(row["audience"].get("kind"))
    iso = lambda d: d.isoformat() if d else None     # noqa: E731
    return {"id": str(row["id"]), "name": row["name"], "audience": row["audience"],
            "audience_label": aud.label if aud else row["audience"].get("kind"), "status": row["status"],
            "status_label": STATUS_LABELS[row["status"]], "channel": row["channel"],
            "scheduled_at": iso(row["scheduled_at"]), "created_at": iso(row["created_at"]), "sent_at": iso(row["sent_at"]),
            "stats": {k: int(row[k]) for k in ("recipients", "sent", "skipped", "failed", "converted")}
            | {"revenue": float(row["revenue"])}}


def list_campaigns(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute(_SUMMARY.format(where=""), {"t": tenant_id, "paid": PAID, "attr": ATTRIBUTION_DAYS})
    return [_summary(r) for r in cur.fetchall()]


def get(cur: Any, tenant_id: str, campaign_id: str) -> Optional[dict[str, Any]]:
    cur.execute(_SUMMARY.format(where="and c.id = %(id)s"),
                {"t": tenant_id, "paid": PAID, "attr": ATTRIBUTION_DAYS, "id": campaign_id})
    row = cur.fetchone()
    if row is None:
        return None
    view = _summary(row)
    cur.execute("select message from campaigns where tenant_id = %s and id = %s", (tenant_id, campaign_id))
    view["message"] = cur.fetchone()["message"]
    cur.execute(
        "select r.name, r.detail, r.status, r.reason, r.sent_at, r.message, exists (select 1 from orders o "
        " join conversations oc on oc.tenant_id = o.tenant_id and oc.id = o.conversation_id where r.status = 'sent' "
        " and o.tenant_id = r.tenant_id and o.status = any(%s) and o.paid_at > r.sent_at "
        " and o.paid_at <= r.sent_at + make_interval(days => %s) and (oc.id = r.conversation_id "
        " or (r.customer_id is not null and oc.customer_id = r.customer_id))) as converted "
        "from campaign_recipients r where r.tenant_id = %s and r.campaign_id = %s order by r.created_at, r.name limit 500",
        (PAID, ATTRIBUTION_DAYS, tenant_id, campaign_id))
    view["recipients"] = [{"name": r["name"], "detail": r["detail"], "status": r["status"], "reason": r["reason"],
                           "sent_at": r["sent_at"].isoformat() if r["sent_at"] else None, "message": r["message"],
                           "converted": r["converted"]} for r in cur.fetchall()]
    return view


def create(cur: Any, tenant_id: str, uid: str, body: dict[str, Any]) -> dict[str, Any]:
    audience = clean_audience(body.get("audience"))
    message = _clean_message(body.get("message"))
    name = str(body.get("name") or AUDIENCES[audience["kind"]].label).strip()[:80]
    cur.execute("insert into campaigns (tenant_id, name, audience, message, channel, created_by) "
                "values (%s, %s, %s::jsonb, %s, %s, %s) returning id",
                (tenant_id, name, json.dumps(audience), message, _enabled_channels()[0], uid))
    campaign_id = str(cur.fetchone()["id"])
    opportunities._audit(cur, tenant_id, "campaign_created", campaign_id, {"actor": uid, "kind": audience["kind"]})
    return get(cur, tenant_id, campaign_id)


def _parse_when(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("La fecha de envío no es válida.") from None
    if when.tzinfo is None:
        raise ValueError("La fecha de envío tiene que tener zona horaria.")
    if (when - datetime.now(timezone.utc)).days > 60:
        raise ValueError("Se puede programar hasta 60 días adelante.")
    return when


def launch(cur: Any, tenant_id: str, uid: str, campaign_id: str, scheduled_at: Any) -> Optional[dict[str, Any]]:
    when = _parse_when(scheduled_at)
    cur.execute("select 1 from tenants where id = %s for update", (tenant_id,))     # tope sin carreras
    cur.execute("select count(*) as n from audit_events where tenant_id = %s and event_type = 'campaign_launched' "
                "and created_at > now() - interval '1 day'", (tenant_id,))
    if cur.fetchone()["n"] >= MAX_LAUNCHES_PER_DAY:
        raise ValueError(f"Podés lanzar hasta {MAX_LAUNCHES_PER_DAY} campañas por día.")
    cur.execute("update campaigns set status = 'scheduled', scheduled_at = coalesce(%s, now()), updated_at = now() "
                "where tenant_id = %s and id = %s and status = 'draft' returning id", (when, tenant_id, campaign_id))
    if cur.fetchone() is None:
        cur.execute("select status from campaigns where tenant_id = %s and id = %s", (tenant_id, campaign_id))
        if cur.fetchone() is None:
            return None
        raise ValueError("Esta campaña ya fue lanzada.")
    opportunities._audit(cur, tenant_id, "campaign_launched", campaign_id,
                         {"actor": uid, "scheduled_at": when.isoformat() if when else None})
    return get(cur, tenant_id, campaign_id)


def cancel(cur: Any, tenant_id: str, uid: str, campaign_id: str) -> Optional[dict[str, Any]]:
    """Cancela antes de enviar; si está enviando, frena lo que falta (lo enviado, enviado está)."""
    cur.execute("update campaigns set status = 'cancelled', updated_at = now() where tenant_id = %s and id = %s "
                "and status in ('draft', 'scheduled', 'sending') returning id", (tenant_id, campaign_id))
    if cur.fetchone() is None:
        cur.execute("select status from campaigns where tenant_id = %s and id = %s", (tenant_id, campaign_id))
        if cur.fetchone() is None:
            return None
        raise ValueError("Esta campaña ya terminó.")
    cur.execute("update campaign_recipients set status = 'skipped', reason = 'campaña cancelada' "
                "where tenant_id = %s and campaign_id = %s and status = 'pending'", (tenant_id, campaign_id))
    opportunities._audit(cur, tenant_id, "campaign_cancelled", campaign_id, {"actor": uid})
    return get(cur, tenant_id, campaign_id)


# --- Baja (la pide el cliente en la charla) -------------------------------------------------
def opt_out(tenant_id: str, conversation_id: str) -> None:
    with tenant_tx(tenant_id) as cur:
        cur.execute("update conversations set marketing_opt_out_at = coalesce(marketing_opt_out_at, now()) "
                    "where tenant_id = %s and id = %s returning customer_id", (tenant_id, conversation_id))
        row = cur.fetchone()
        if row and row["customer_id"]:
            cur.execute("update demo_customers set opt_out_at = coalesce(opt_out_at, now()) "
                        "where tenant_id = %s and id = %s", (tenant_id, row["customer_id"]))
        opportunities._audit(cur, tenant_id, "marketing_opt_out", conversation_id, {})


# --- Worker ---------------------------------------------------------------------------------
def _send_simulated(recipient: dict[str, Any]) -> Optional[str]:
    """No sale nada del sistema: el destinatario queda como «enviado (simulado)»."""
    return None


_CHANNELS: dict[str, Callable[[dict[str, Any]], Optional[str]]] = {"simulado": _send_simulated}


def _materialize(tenant_id: str, campaign_id: str) -> None:
    """Pasa a «enviando» y congela la audiencia en la MISMA transacción: si algo falla, la campaña
    sigue programada y se reintenta; si la cancelaron en el medio, no se arma nada."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("update campaigns set status = 'sending', started_at = now(), updated_at = now() "
                    "where tenant_id = %s and id = %s and status = 'scheduled' returning audience, message",
                    (tenant_id, campaign_id))
        c = cur.fetchone()
        if c is None:
            return
        store = _store(cur, tenant_id)
        rows = [r for r in _rows(cur, tenant_id, c["audience"], MAX_RECIPIENTS * 2) if not r["opted_out"] and not r["recent"]]
        for r in rows[:MAX_RECIPIENTS]:
            cur.execute("insert into campaign_recipients (tenant_id, campaign_id, conversation_id, customer_id, order_id, "
                        "name, detail, message) values (%s, %s, %s, %s, %s, %s, %s, %s) on conflict do nothing",
                        (tenant_id, campaign_id, r["conversation_id"], r["customer_id"], r["order_id"],
                         (r["name"] or "Cliente")[:80], _detail(c["audience"]["kind"], r), render(c["message"], r, store)))


def _recently_sent(cur: Any, tenant_id: str, campaign_id: str, r: dict[str, Any]) -> Optional[str]:
    """Tope de frecuencia al ENVIAR (dos campañas armadas a la vez no le escriben dos veces)."""
    cur.execute("select 1 from campaign_recipients x where x.tenant_id = %s and x.campaign_id <> %s and x.status = 'sent' "
                "and x.sent_at > now() - make_interval(days => %s) and (x.conversation_id = %s "
                "or (%s::uuid is not null and x.customer_id = %s::uuid)) limit 1",
                (tenant_id, campaign_id, FREQUENCY_DAYS, r["conversation_id"], r["customer_id"], r["customer_id"]))
    return "ya recibió otra campaña esta semana" if cur.fetchone() else None


def _send_batch(tenant_id: str, campaign_id: str, channel: str) -> int:
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select r.id, r.conversation_id, r.customer_id, r.message, (dc.opt_out_at is not null or cv.marketing_opt_out_at is not null "
            " or coalesce(dc.consent_status, '') in ('opted_out', 'denied') or cv.blocked_at is not null) as opted_out "
            "from campaign_recipients r "
            "join conversations cv on cv.tenant_id = r.tenant_id and cv.id = r.conversation_id "
            "left join demo_customers dc on dc.tenant_id = r.tenant_id and dc.id = r.customer_id "
            "where r.tenant_id = %s and r.campaign_id = %s and r.status = 'pending' "
            "order by r.created_at limit %s for update of r skip locked", (tenant_id, campaign_id, SEND_BATCH))
        batch = cur.fetchall()
        send = _CHANNELS.get(channel)
        for r in batch:
            skip = "se dio de baja" if r["opted_out"] else _recently_sent(cur, tenant_id, campaign_id, r)
            if skip:
                cur.execute("update campaign_recipients set status = 'skipped', reason = %s where tenant_id = %s and id = %s",
                            (skip, tenant_id, r["id"]))
                continue
            error = send(r) if send else "canal no habilitado"
            cur.execute("update campaign_recipients set status = %s, reason = %s, sent_at = case when %s then now() end "
                        "where tenant_id = %s and id = %s", ("failed" if error else "sent", error, error is None, tenant_id, r["id"]))
        if len(batch) < SEND_BATCH:
            cur.execute("update campaigns set status = 'sent', sent_at = now(), updated_at = now() "
                        "where tenant_id = %s and id = %s and status = 'sending'", (tenant_id, campaign_id))
        return len(batch)


def dispatch_due(budget_s: float = WORKER_BUDGET_S) -> int:
    """Una pasada del worker: arranca las campañas vencidas (congela su audiencia) y envía una tanda de
    cada campaña en curso, de a una campaña por vez (ningún negocio acapara la pasada)."""
    started, done = time.monotonic(), 0
    while time.monotonic() - started < budget_s:
        with system_tx() as cur:     # la reclama 5 min: otro worker no la toma; si falla, se reintenta
            cur.execute("update campaigns set scheduled_at = now() + interval '5 minutes' where id = ("
                        " select id from campaigns where status = 'scheduled' and scheduled_at <= now() "
                        " order by scheduled_at for update skip locked limit 1) returning id, tenant_id")
            row = cur.fetchone()
        if row is None:
            break
        try:
            _materialize(str(row["tenant_id"]), str(row["id"]))
        except Exception:
            log.exception("campaña %s: no se pudo armar la audiencia; se reintenta", row["id"])
    with system_tx() as cur:
        cur.execute("select id, tenant_id, channel from campaigns where status = 'sending' order by updated_at limit 50")
        sending = cur.fetchall()
    for c in sending:
        if time.monotonic() - started >= budget_s:
            break
        try:
            done += _send_batch(str(c["tenant_id"]), str(c["id"]), c["channel"])
        except Exception:
            log.exception("campaña %s: falló una tanda; se reintenta", c["id"])
    return done
