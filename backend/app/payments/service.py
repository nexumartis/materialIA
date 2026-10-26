"""Cobro de pedidos: link de pago idempotente y aplicación VERIFICADA de avisos del proveedor.

Un pedido pasa a PAID sólo si el proveedor, consultado por API, informa `approved` por el monto y
la moneda del pedido. El negocio (tenant) se deriva del pedido real referenciado por el pago,
nunca del cuerpo del aviso. Aplicar el mismo pago dos veces no tiene efecto.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from ..db import system_tx, tenant_tx
from ..domain import inventory, opportunities, orders
from ..domain.inventory import OutOfStock
from ..schemas import OpportunityInput
from .providers import PaymentProviderError, ProviderPayment, get_provider

log = logging.getLogger(__name__)

_FINAL_FAILURES = {"rejected", "cancelled"}
_REVERSALS = {"refunded", "charged_back"}


def start_payment(tenant_id: str, order_id: str) -> dict[str, Any]:
    """Devuelve el link de pago del pedido PENDING_PAYMENT; lo crea una sola vez.

    El pedido queda bloqueado mientras se crea la preferencia: dos confirmaciones simultáneas
    no generan dos links. Si el proveedor falla, no queda nada a medias (se puede reintentar).
    """
    provider = get_provider()
    with tenant_tx(tenant_id) as cur:
        row = orders._fetch(cur, tenant_id, order_id, lock=True)
        if row is None or row["status"] != "PENDING_PAYMENT":
            raise ValueError("el pedido no está esperando pago")
        # Un solo link por pedido: tras un pago rechazado el cliente reintenta en la misma
        # preferencia (Mercado Pago lo permite), sin chocar con su idempotency key.
        cur.execute(
            "select provider, checkout_url from payments where tenant_id = %s and order_id = %s "
            "and provider = %s and checkout_url is not null order by created_at limit 1",
            (tenant_id, order_id, provider.name),
        )
        existing = cur.fetchone()
        if existing:
            return {"provider": existing["provider"], "checkout_url": existing["checkout_url"]}
        view = orders._view(cur, row)
        checkout = provider.create_checkout(view)   # PaymentProviderError => rollback
        cur.execute(
            "insert into payments (tenant_id, order_id, provider, preference_id, checkout_url, amount, currency) "
            "values (%s, %s, %s, %s, %s, %s, %s)",
            (tenant_id, order_id, provider.name, checkout.preference_id, checkout.url,
             view["total"], view["currency"]),
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


def apply_payment(provider_name: str, payment: ProviderPayment) -> str:
    """Aplica el estado verificado de un pago a su pedido. Idempotente."""
    tenant_id = _order_tenant(payment.external_reference)
    if tenant_id is None:
        return "pedido inexistente"
    became_paid = None
    with tenant_tx(tenant_id) as cur:
        order = orders._fetch(cur, tenant_id, payment.external_reference, lock=True)
        order_id = str(order["id"])
        _record_payment(cur, tenant_id, order_id, provider_name, payment)

        if payment.status == "approved":
            # Sólo cuenta como cobro previo un pago aprobado por el monto y la moneda del pedido
            # (uno con monto distinto ya quedó en revisión y no cumple el pedido).
            cur.execute(
                "select 1 from payments where tenant_id = %s and order_id = %s and status = 'approved' "
                "and provider_payment_id is distinct from %s and abs(amount - %s) <= 0.005 "
                "and currency = %s limit 1",
                (tenant_id, order_id, payment.id, order["total"], order["currency"]),
            )
            if cur.fetchone():
                # Otro pago aprobado distinto para el mismo pedido: cobro doble => una persona.
                _attention(cur, tenant_id, order_id, "duplicate_payment")
                return "pago duplicado: requiere devolución"
            if order["status"] in ("PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"):
                return "ya estaba pagado"
            if (abs(payment.amount - float(order["total"])) > 0.005
                    or payment.currency != order["currency"]):
                _attention(cur, tenant_id, order_id, "amount_mismatch")
                return "monto o moneda no coinciden: requiere revisión"
            lines = [(it["item_id"], it["qty"]) for it in orders._items(cur, tenant_id, order_id)]
            if order["status"] == "CANCELLED":
                # Pago tardío: la reserva venció. Se intenta apartar de nuevo, sin vender de más.
                try:
                    with cur.connection.transaction():
                        inventory._reserve(cur, tenant_id, order_id, lines)
                except OutOfStock:
                    _attention(cur, tenant_id, order_id, "paid_without_stock")
                    return "pagado sin stock: requiere devolución"
            elif order["status"] != "PENDING_PAYMENT":
                _attention(cur, tenant_id, order_id, f"paid_in_status_{order['status'].lower()}")
                return "pago en un estado inesperado: requiere revisión"
            inventory._sell(cur, tenant_id, order_id, lines)
            if order["attention_reason"]:
                # Se resolvió (p. ej. pago tardío reintentado con stock repuesto): queda auditado.
                opportunities._audit(cur, tenant_id, "order_attention_resolved", order_id,
                                     {"reason": order["attention_reason"]})
            cur.execute(
                "update orders set status = 'PAID', paid_at = now(), cancel_reason = null, "
                "attention_reason = null, updated_at = now() where tenant_id = %s and id = %s",
                (tenant_id, order_id),
            )
            became_paid = orders._view(cur, orders._fetch(cur, tenant_id, order_id))
            became_paid["conversation_id"] = (str(order["conversation_id"])
                                              if order["conversation_id"] else None)
        elif payment.status in _REVERSALS:
            if order["status"] in ("PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"):
                cur.execute(
                    "update orders set status = 'REFUNDED', updated_at = now() "
                    "where tenant_id = %s and id = %s", (tenant_id, order_id))
                _attention(cur, tenant_id, order_id, f"payment_{payment.status}")
            return f"pago {payment.status}"
        else:
            # pending / in_process / rejected / cancelled: el pedido sigue esperando pago hasta
            # que se pague o venza la reserva; el cliente puede reintentar con el mismo link.
            return f"pago {payment.status}" + (" (sin cambios en el pedido)"
                                                if payment.status in _FINAL_FAILURES else "")

    _after_paid(tenant_id, became_paid)
    return "pedido pagado"


def _record_payment(cur: Any, tenant_id: str, order_id: str, provider_name: str,
                    payment: ProviderPayment) -> None:
    cur.execute(
        "update payments set status = %s, amount = %s, currency = %s, updated_at = now() "
        "where tenant_id = %s and provider = %s and provider_payment_id = %s",
        (payment.status, payment.amount, payment.currency, tenant_id, provider_name, payment.id),
    )
    if cur.rowcount:
        return
    cur.execute(
        "update payments set provider_payment_id = %s, status = %s, amount = %s, currency = %s, "
        "updated_at = now() "
        "where id = (select id from payments where tenant_id = %s and order_id = %s and provider = %s "
        "and provider_payment_id is null order by created_at desc limit 1)",
        (payment.id, payment.status, payment.amount, payment.currency, tenant_id, order_id,
         provider_name),
    )
    if cur.rowcount:
        return
    cur.execute(
        "insert into payments (tenant_id, order_id, provider, provider_payment_id, status, amount, currency) "
        "values (%s, %s, %s, %s, %s, %s, %s)",
        (tenant_id, order_id, provider_name, payment.id, payment.status, payment.amount, payment.currency),
    )


def _attention(cur: Any, tenant_id: str, order_id: str, reason: str) -> None:
    cur.execute("update orders set attention_reason = %s, updated_at = now() "
                "where tenant_id = %s and id = %s", (reason, tenant_id, order_id))
    opportunities._audit(cur, tenant_id, "order_needs_attention", order_id, {"reason": reason})


def _after_paid(tenant_id: str, order: dict[str, Any]) -> None:
    """Efectos posteriores al pago (fuera de la transacción del cobro): aviso al cliente en su
    conversación y CRM. Si fallan, el pedido igual queda pagado y se registra el error."""
    conv = order.get("conversation_id")
    try:
        opportunities.audit(tenant_id, "order_paid", order["id"], {"number": order["number"]})
        if conv:
            opportunities.add_message(
                tenant_id, conv, "outbound",
                f"¡Pago confirmado! Tu pedido #{order['number']} quedó pagado. "
                "Te aviso cuando salga.")
            opp = opportunities.upsert_opportunity(tenant_id, OpportunityInput(
                conversation_id=conv, stage="cerrada", origin="venta_chat",
                requirements={"pedido": order["number"]}, requires_human_quote=False,
                estimated_amount=order["total"]))
            opportunities.log_activity(tenant_id, opp.id, "pago_confirmado",
                                       f"pedido #{order['number']} pagado")
    except Exception:  # noqa: BLE001 - el cobro ya está firme; sólo se registra
        log.exception("efectos posteriores al pago fallaron para el pedido %s", order["id"])
