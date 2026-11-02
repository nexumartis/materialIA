"""Cobro de pedidos: link de pago idempotente y aplicación VERIFICADA de avisos del proveedor.

Un pedido pasa a PAID sólo si el proveedor, consultado por API, informa `approved` por el monto y
la moneda del pedido. El negocio (tenant) se deriva del pedido real referenciado por el pago,
nunca del cuerpo del aviso. Aplicar el mismo pago dos veces no tiene efecto.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Optional, Sequence

from psycopg.errors import UniqueViolation

from ..db import system_tx, tenant_tx
from ..documents import store
from ..domain import inventory, opportunities, orders, receipts
from ..domain.inventory import OutOfStock
from ..schemas import OpportunityInput
from .providers import PaymentProviderError, ProviderPayment, get_provider

log = logging.getLogger(__name__)

_FINAL_FAILURES = {"rejected", "cancelled"}
_REVERSALS = {"refunded", "charged_back"}
_PAID_STATES = ("PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED")


def _charge_view(view: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Lo que se le pide al proveedor: el pedido entero o, con seña, la seña o el saldo como un
    único ítem (con su propia clave de idempotencia)."""
    amount, kind = orders.amount_due(row)
    if kind == "total":
        return view
    label = "Seña" if kind == "deposit" else "Saldo"
    return {**view, "total": amount, "charge": kind,
            "items": [{"sku": f"{kind.upper()}-{view['number']}", "name": f"{label} del pedido #{view['number']}",
                       "qty": 1, "unit_price": amount}]}


def start_payment(tenant_id: str, order_id: str) -> dict[str, Any]:
    """Devuelve el link de pago de lo que el pedido debe ahora (pedido, seña o saldo); lo crea una
    sola vez por cobro.

    El pedido queda bloqueado mientras se crea la preferencia: dos confirmaciones simultáneas
    no generan dos links. Si el proveedor falla, no queda nada a medias (se puede reintentar).
    """
    provider = get_provider()
    with tenant_tx(tenant_id) as cur:
        row = orders._fetch(cur, tenant_id, order_id, lock=True)
        if row is None or row["status"] not in orders.AWAITING_PAYMENT:
            raise ValueError("el pedido no está esperando pago")
        due, kind = orders.amount_due(row)
        # Un solo link por pedido: tras un pago rechazado el cliente reintenta en la misma
        # preferencia (Mercado Pago lo permite), sin chocar con su idempotency key.
        cur.execute(
            "select provider, checkout_url from payments where tenant_id = %s and order_id = %s "
            "and provider = %s and checkout_url is not null and coalesce(charge, 'total') = %s "
            "order by created_at limit 1",
            (tenant_id, order_id, provider.name, kind),
        )
        existing = cur.fetchone()
        if existing:
            return {"provider": existing["provider"], "checkout_url": existing["checkout_url"]}
        view = _charge_view(orders._view(cur, row), row)
        checkout = provider.create_checkout(view)   # PaymentProviderError => rollback
        cur.execute(
            "insert into payments (tenant_id, order_id, provider, preference_id, checkout_url, amount, currency, "
            "charge) values (%s, %s, %s, %s, %s, %s, %s, %s)",
            (tenant_id, order_id, provider.name, checkout.preference_id, checkout.url,
             due, view["currency"], None if kind == "total" else kind),
        )
    return {"provider": provider.name, "checkout_url": checkout.url}


def receive_notification(provider_name: str, headers: dict[str, str], query: dict[str, str],
                         body: dict[str, Any]) -> tuple[int, str]:
    """Punto de entrada de los webhooks. Devuelve (status HTTP, resultado).

    401 si la firma no verifica; 200 para avisos procesados o ignorables; 503 si el proveedor no
    respondió (el proveedor reintenta)."""
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    data_id = str(query.get("data.id") or data.get("id") or "")
    kind = str(query.get("type") or body.get("type") or "")
    request_id = {k.lower(): v for k, v in headers.items()}.get("x-request-id")
    try:
        provider = get_provider(provider_name)
    except PaymentProviderError:
        return 404, "proveedor desconocido o no configurado"

    if not provider.verify_notification(headers, data_id):
        # Sin firma válida no se escribe nada (evita llenar la tabla con avisos falsos).
        log.warning("aviso de %s con firma inválida (request-id %s)", provider_name, request_id)
        return 401, "firma inválida"
    outcome = "error al procesar"
    try:
        if kind != "payment":
            outcome = f"ignorado ({kind or 'sin tipo'})"
            return 200, outcome
        try:
            payment = provider.fetch_payment(data_id)
        except PaymentProviderError:
            outcome = "proveedor no disponible"
            return 503, outcome
        if payment is None:
            outcome = "pago inexistente en el proveedor"
            return 200, outcome
        outcome = apply_payment(provider.name, payment)
        return 200, outcome
    finally:
        with system_tx() as cur:
            cur.execute(
                "insert into payment_notifications (provider, request_id, resource_id, signature_ok, outcome) "
                "values (%s, %s, %s, true, %s)",
                (provider_name, request_id, data_id or None, outcome),
            )


def _order_tenant(order_id: str) -> Optional[str]:
    try:
        uuid.UUID(order_id)
    except ValueError:
        return None
    with system_tx() as cur:
        cur.execute("select tenant_id from orders where id = %s", (order_id,))
        r = cur.fetchone()
    return str(r["tenant_id"]) if r else None


class ReferenceInUse(ValueError):
    """La referencia bancaria ya acreditó otro pedido del negocio (409)."""


_TRANSFER_REF = re.compile(r"[A-Z0-9-]{4,64}")


def apply_payment(provider_name: str, payment: ProviderPayment) -> str:
    """Aplica el estado verificado de un pago a su pedido. Idempotente."""
    tenant_id = _order_tenant(payment.external_reference)
    if tenant_id is None:
        return "pedido inexistente"
    with tenant_tx(tenant_id) as cur:
        order = orders._fetch(cur, tenant_id, payment.external_reference, lock=True)
        outcome, became_paid = _apply(cur, tenant_id, order, provider_name, payment)
    if became_paid:
        _after_paid(tenant_id, became_paid)
    if outcome == DEPOSIT_OK:
        _offer_balance(tenant_id, payment.external_reference)
    return outcome


def confirm_transfer(tenant_id: str, uid: str, order_id: str, reference: str,
                     amount: float, currency: str, document_ids: Sequence[str] = ()) -> str:
    """El dueño acredita una transferencia que cotejó en su banco. Mismo efecto que un pago
    verificado por el proveedor (stock, pedido, constancia), con actor y fecha auditados.

    `tenant_id` lo resuelve el servidor; igual se revalida la membresía de `uid` (PermissionError).
    Pedido inexistente => LookupError; referencia ya usada en otro pedido => ReferenceInUse.
    `document_ids`: comprobantes del pedido que el dueño cotejó; se asocian sólo si el pago queda
    acreditado. Importe/moneda distintos del pedido o un pedido ya pagado => ValueError sin escribir
    nada: el dueño sólo acredita lo que cubre el pedido (un error de tipeo no es plata recibida)."""
    ref = re.sub(r"\s+", "", reference or "").upper()
    if not _TRANSFER_REF.fullmatch(ref):
        raise ValueError("referencia inválida (4 a 64 letras, números o guiones)")
    if not amount or amount <= 0:
        raise ValueError("importe inválido")
    payment = ProviderPayment(id=f"{tenant_id}:{ref}", status="approved", external_reference=order_id,
                              amount=float(amount), currency=(currency or "").upper())
    try:
        with tenant_tx(tenant_id) as cur:
            cur.execute("select 1 from memberships where user_id = %s and tenant_id = %s for share",
                        (uid, tenant_id))
            if cur.fetchone() is None:
                raise PermissionError("sin acceso a este negocio")
            order = orders._fetch(cur, tenant_id, order_id, lock=True)
            if order is None:
                raise LookupError("pedido inexistente")
            cur.execute("select order_id from payments where provider = 'transfer' and provider_payment_id = %s",
                        (payment.id,))
            same = cur.fetchone()
            if same is not None and str(same["order_id"]) != order_id:
                raise ReferenceInUse("esa referencia ya acreditó otro pedido")
            if same is None:   # transferencia nueva: tiene que cubrir exactamente un pedido impago
                if order["status"] in _PAID_STATES:
                    raise ValueError("el pedido ya figura pagado")
                if not _amount_ok(order, payment) or payment.currency != order["currency"]:
                    due = " o ".join(f"{a:.2f}" for a in _accepted(order))
                    raise ValueError(f"el importe o la moneda no coinciden con lo que debe el pedido "
                                     f"({due} {order['currency']})")
            outcome, became_paid = _apply(cur, tenant_id, order, "transfer", payment, verified_by=uid)
            if became_paid or outcome == "ya estaba pagado":
                cur.execute("select id from payments where tenant_id = %s and provider = 'transfer' "
                            "and provider_payment_id = %s", (tenant_id, payment.id))
                store.link(cur, tenant_id, uid, order_id, str(cur.fetchone()["id"]), list(document_ids))
            opportunities._audit(cur, tenant_id, "transfer_confirmed", order_id,
                                 {"actor": uid, "reference": ref, "amount": payment.amount,
                                  "currency": payment.currency, "outcome": outcome,
                                  "documents": list(document_ids)})
    except UniqueViolation:
        # Otra transacción ya registró esa referencia en otro pedido: rollback completo.
        raise ReferenceInUse("esa referencia ya acreditó otro pedido") from None
    if became_paid:
        _after_paid(tenant_id, became_paid)
    if outcome == DEPOSIT_OK:
        _offer_balance(tenant_id, order_id)
    return outcome


DEPOSIT_OK = "seña acreditada"


def _accepted(order: dict[str, Any]) -> list[float]:
    """Montos que un pago puede cubrir según el estado: con seña pendiente, la seña o todo junto;
    señado, el saldo; si no, el total."""
    total = float(order["total"])
    if order.get("deposit") is not None and order["status"] in ("PENDING_PAYMENT", "CANCELLED"):
        return [float(order["deposit"]), total]      # cancelado: seña tardía de una cotización vencida
    if order["status"] == "DEPOSIT_PAID":
        return [orders.amount_due(order)[0]]
    return [total]


def _amount_ok(order: dict[str, Any], payment: ProviderPayment) -> bool:
    return any(abs(payment.amount - a) <= 0.005 for a in _accepted(order))


def _offer_balance(tenant_id: str, order_id: str) -> None:
    """Después de la seña, deja en la conversación el link del saldo. Si el proveedor falla, el
    cliente lo pide después («link de pago») y el agente lo reintenta."""
    try:
        pay = start_payment(tenant_id, order_id)
    except (PaymentProviderError, ValueError):
        log.warning("no se pudo generar el link del saldo del pedido %s", order_id)
        return
    with tenant_tx(tenant_id) as cur:
        order = orders._fetch(cur, tenant_id, order_id)
        if order is None or order["status"] != "DEPOSIT_PAID" or not order["conversation_id"]:
            return
        due = orders.amount_due(order)[0]
        _message(cur, tenant_id, order["conversation_id"],
                 f"Cuando quieras pagar el saldo de {_ars(due)} del pedido #{order['number']}: "
                 f"{pay['checkout_url']}",
                 {"type": "balance_link", "order_id": order_id})


def _ars(amount: float) -> str:
    return "$" + f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _apply(cur: Any, tenant_id: str, order: dict[str, Any], provider_name: str,
           payment: ProviderPayment, verified_by: Optional[str] = None) -> tuple[str, Optional[dict[str, Any]]]:
    """Efecto de un pago verificado sobre su pedido (bloqueado por el llamador).
    Devuelve (resultado, pedido recién pagado o None)."""
    order_id = str(order["id"])
    cur.execute("select status from payments where tenant_id = %s and order_id = %s and provider = %s "
                "and provider_payment_id = %s", (tenant_id, order_id, provider_name, payment.id))
    before = cur.fetchone()
    payment_id = _record_payment(cur, tenant_id, order_id, provider_name, payment, verified_by)

    if payment.status in _REVERSALS:
        if order["status"] in _PAID_STATES:
            if _other_valid_payment(cur, tenant_id, order, payment.id):
                # Se devolvió un cobro sobrante (p. ej. el duplicado): otro pago sigue cubriendo el pedido.
                if order["attention_reason"] == "duplicate_payment":
                    cur.execute("update orders set attention_reason = null, updated_at = now() "
                                "where tenant_id = %s and id = %s", (tenant_id, order_id))
                    opportunities._audit(cur, tenant_id, "order_attention_resolved", order_id,
                                         {"reason": "duplicate_payment"})
            elif _others_total(cur, tenant_id, order, payment.id) > 0.005:
                # Devolución parcial (p. ej. sólo la seña): sigue habiendo plata cobrada; lo resuelve
                # una persona sin anular el pedido ni la constancia.
                _attention(cur, tenant_id, order, f"payment_{payment.status}", notify=False)
            else:
                cur.execute(
                    "update orders set status = 'REFUNDED', updated_at = now() "
                    "where tenant_id = %s and id = %s", (tenant_id, order_id))
                _attention(cur, tenant_id, order, f"payment_{payment.status}", notify=False)
        elif order["status"] == "DEPOSIT_PAID":
            # Se devolvió la seña: el pedido ya no está señado; lo resuelve una persona.
            cur.execute("update orders set status = 'REFUNDED', updated_at = now() "
                        "where tenant_id = %s and id = %s", (tenant_id, order_id))
            _attention(cur, tenant_id, order, f"payment_{payment.status}", notify=False)
        return f"pago {payment.status}", None
    if payment.status != "approved":
        # pending / in_process / rejected / cancelled: el pedido sigue esperando pago hasta
        # que se pague o venza la reserva; el cliente puede reintentar con el mismo link.
        return f"pago {payment.status}" + (" (sin cambios en el pedido)"
                                            if payment.status in _FINAL_FAILURES else ""), None

    if _other_valid_payment(cur, tenant_id, order, payment.id):
        # Otro pago aprobado distinto para el mismo pedido: cobro doble => una persona.
        _attention(cur, tenant_id, order, "duplicate_payment")
        return "pago duplicado: requiere devolución", None
    if order["status"] in _PAID_STATES:
        return "ya estaba pagado", None
    if order["status"] == "DEPOSIT_PAID" and before and before["status"] == "approved":
        return "seña ya acreditada", None     # el mismo pago de la seña, reenviado: no es el saldo
    if not _amount_ok(order, payment) or payment.currency != order["currency"]:
        _attention(cur, tenant_id, order, "amount_mismatch")
        return "monto o moneda no coinciden: requiere revisión", None
    if (order["status"] in ("PENDING_PAYMENT", "CANCELLED") and order.get("deposit") is not None
            and abs(payment.amount - float(order["deposit"])) <= 0.005):
        cur.execute("update orders set status = 'DEPOSIT_PAID', deposit_paid_at = now(), reserved_until = null, "
                    "cancel_reason = null, attention_reason = null, updated_at = now() "
                    "where tenant_id = %s and id = %s",
                    (tenant_id, order_id))
        cur.execute("update payments set charge = 'deposit' where tenant_id = %s and id = %s", (tenant_id, payment_id))
        opportunities._audit(cur, tenant_id, "order_deposit_paid", order_id,
                             {"amount": payment.amount, "provider": provider_name})
        if order["conversation_id"]:
            _message(cur, tenant_id, order["conversation_id"],
                     f"¡Recibimos la seña del pedido #{order['number']}! Ya quedó señado; "
                     "falta pagar el saldo.", {"type": "deposit_paid", "order_id": order_id})
        return DEPOSIT_OK, None
    # Un pedido a medida no aparta ni descuenta stock: se fabrica o se encarga.
    lines = ([] if order.get("quote")
             else [(it["item_id"], it["qty"]) for it in orders._items(cur, tenant_id, order_id)])
    if order["status"] == "CANCELLED":
        # Pago tardío: la reserva venció. Se intenta apartar de nuevo, sin vender de más.
        try:
            with cur.connection.transaction():
                inventory._reserve(cur, tenant_id, order_id, lines)
        except OutOfStock:
            _attention(cur, tenant_id, order, "paid_without_stock")
            return "pagado sin stock: requiere devolución", None
    elif order["status"] not in orders.AWAITING_PAYMENT:
        _attention(cur, tenant_id, order, f"paid_in_status_{order['status'].lower()}")
        return "pago en un estado inesperado: requiere revisión", None
    inventory._sell(cur, tenant_id, order_id, lines)
    if order["status"] == "DEPOSIT_PAID":
        cur.execute("update payments set charge = 'balance' where tenant_id = %s and id = %s", (tenant_id, payment_id))
    if order["attention_reason"]:
        # Se resolvió (p. ej. pago tardío reintentado con stock repuesto): queda auditado.
        opportunities._audit(cur, tenant_id, "order_attention_resolved", order_id,
                             {"reason": order["attention_reason"]})
    cur.execute(
        "update orders set status = 'PAID', paid_at = now(), cancel_reason = null, "
        "attention_reason = null, updated_at = now() where tenant_id = %s and id = %s",
        (tenant_id, order_id),
    )
    # Constancia + aviso al cliente en ESTA transacción: si algo falla después, no se pierden;
    # si el pago se reaplica, no se duplican (una constancia por pedido).
    receipt_id = receipts.issue(cur, tenant_id, order_id, payment_id)
    if receipt_id and order["conversation_id"]:
        _message(cur, tenant_id, order["conversation_id"],
                 f"¡Pago confirmado! Tu pedido #{order['number']} quedó pagado y ya tenés tu "
                 "constancia de compra. Para ver cómo sigue, escribime «¿cómo va mi pedido?».",
                 {"type": "receipt", "receipt_id": receipt_id})
    became_paid = orders._view(cur, orders._fetch(cur, tenant_id, order_id))
    became_paid["conversation_id"] = str(order["conversation_id"]) if order["conversation_id"] else None
    return "pedido pagado", became_paid


def _others_total(cur: Any, tenant_id: str, order: dict[str, Any], payment_id: str) -> float:
    """Suma de los OTROS pagos aprobados del pedido en su moneda (con seña son dos: seña y saldo)."""
    cur.execute(
        "select coalesce(sum(amount), 0) as s from payments where tenant_id = %s and order_id = %s "
        "and status = 'approved' and provider_payment_id is distinct from %s and currency = %s",
        (tenant_id, str(order["id"]), payment_id, order["currency"]),
    )
    return float(cur.fetchone()["s"])


def _other_valid_payment(cur: Any, tenant_id: str, order: dict[str, Any], payment_id: str) -> bool:
    """¿Los otros pagos aprobados (no éste) ya cubren el pedido entero? Entonces éste sobra."""
    return _others_total(cur, tenant_id, order, payment_id) >= float(order["total"]) - 0.005


def _record_payment(cur: Any, tenant_id: str, order_id: str, provider_name: str,
                    payment: ProviderPayment, verified_by: Optional[str] = None) -> str:
    """Registra el estado del pago (por pedido: un id ya usado en OTRO pedido no se toca y choca
    con uq_payments_provider_payment). Devuelve el id de la fila."""
    approved, reversed_ = payment.status == "approved", payment.status in _REVERSALS
    stamps = ("verified_at = case when %s then coalesce(verified_at, now()) else verified_at end, "
              "verified_by = coalesce(verified_by, %s), "
              "reversed_at = case when %s then coalesce(reversed_at, now()) else reversed_at end, ")
    stamp_args = (approved, verified_by if approved else None, reversed_)
    cur.execute(
        f"update payments set status = %s, amount = %s, currency = %s, {stamps}updated_at = now() "
        "where tenant_id = %s and order_id = %s and provider = %s and provider_payment_id = %s returning id",
        (payment.status, payment.amount, payment.currency, *stamp_args, tenant_id, order_id,
         provider_name, payment.id),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute(
            f"update payments set provider_payment_id = %s, status = %s, amount = %s, currency = %s, "
            f"{stamps}updated_at = now() "
            "where id = (select id from payments where tenant_id = %s and order_id = %s and provider = %s "
            "and provider_payment_id is null order by created_at desc limit 1) returning id",
            (payment.id, payment.status, payment.amount, payment.currency, *stamp_args, tenant_id,
             order_id, provider_name),
        )
        row = cur.fetchone()
    if row is None:
        cur.execute(
            "insert into payments (tenant_id, order_id, provider, provider_payment_id, status, amount, "
            "currency, verified_at, verified_by, reversed_at) values (%s, %s, %s, %s, %s, %s, %s, "
            "case when %s then now() end, %s, case when %s then now() end) returning id",
            (tenant_id, order_id, provider_name, payment.id, payment.status, payment.amount,
             payment.currency, *stamp_args),
        )
        row = cur.fetchone()
    return str(row["id"])


def _attention(cur: Any, tenant_id: str, order: dict[str, Any], reason: str, notify: bool = True) -> None:
    """Marca el pedido para revisión humana. El aviso al cliente se persiste una sola vez por
    motivo (los reintentos del proveedor no lo repiten) y no promete avisos que no existen."""
    cur.execute("update orders set attention_reason = %s, updated_at = now() "
                "where tenant_id = %s and id = %s and attention_reason is distinct from %s",
                (reason, tenant_id, order["id"], reason))
    if not cur.rowcount:
        return
    opportunities._audit(cur, tenant_id, "order_needs_attention", str(order["id"]), {"reason": reason})
    if notify and order["conversation_id"]:
        _message(cur, tenant_id, order["conversation_id"],
                 f"Recibimos un pago para tu pedido #{order['number']}, pero antes de confirmarlo "
                 "lo tiene que revisar una persona del negocio. Para ver el estado, escribime "
                 "«¿cómo va mi pedido?».", {"type": "payment_attention", "reason": reason})


def _message(cur: Any, tenant_id: str, conversation_id: Any, content: str, payload: dict[str, Any]) -> None:
    opportunities._add_message(cur, tenant_id, str(conversation_id), "outbound", content, payload)


def _after_paid(tenant_id: str, order: dict[str, Any]) -> None:
    """Efectos posteriores al pago (fuera de la transacción del cobro): auditoría y CRM. El aviso
    al cliente y la constancia ya quedaron en la transacción. Si fallan, el pedido igual queda
    pagado y se registra el error."""
    conv = order.get("conversation_id")
    try:
        opportunities.audit(tenant_id, "order_paid", order["id"], {"number": order["number"]})
        if conv:
            opp = opportunities.upsert_opportunity(tenant_id, OpportunityInput(
                conversation_id=conv, stage="cerrada", origin="venta_chat",
                requirements={"pedido": order["number"]}, requires_human_quote=False,
                estimated_amount=order["total"]))
            opportunities.log_activity(tenant_id, opp.id, "pago_confirmado",
                                       f"pedido #{order['number']} pagado")
    except Exception:  # noqa: BLE001 - el cobro ya está firme; sólo se registra
        log.exception("efectos posteriores al pago fallaron para el pedido %s", order["id"])
