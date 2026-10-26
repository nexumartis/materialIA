"""Carrito, checkout y estados del pedido. Todo scoped por tenant resuelto en servidor.

- El carrito es un pedido en CART_OPEN; hay uno solo por conversación (índice único parcial).
- Agregar al carrito valida precio vigente y disponible, pero NO aparta stock.
- `checkout` revalida precios y stock con el pedido bloqueado: si cambió un precio, actualiza el
  carrito y pide reconfirmar; si falta stock, no aparta nada; si todo da, aparta y pasa a
  PENDING_PAYMENT con vencimiento. Repetirlo sobre un pedido ya pendiente no duplica nada.
- La transición a PAID la hace exclusivamente `payments.service` con el pago verificado.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config import settings
from ..db import system_tx, tenant_tx
from . import inventory
from .inventory import OutOfStock

log = logging.getLogger(__name__)

STATUS_LABELS = {
    "CART_OPEN": "carrito abierto",
    "PENDING_PAYMENT": "esperando el pago",
    "PAID": "pagado, todavía no despachado",
    "PREPARING": "en preparación",
    "DISPATCHED": "despachado",
    "IN_TRANSIT": "en camino",
    "DELIVERED": "entregado",
    "CANCELLED": "cancelado",
    "REFUNDED": "reintegrado",
}

# Avance operativo del pedido después del pago (lo hace el negocio, no el agente).
FULFILLMENT_NEXT = {
    "PAID": {"PREPARING", "DISPATCHED"},
    "PREPARING": {"DISPATCHED"},
    "DISPATCHED": {"IN_TRANSIT", "DELIVERED"},
    "IN_TRANSIT": {"DELIVERED"},
}

_ORDER_COLUMNS = ("id, number, tenant_id, conversation_id, status, currency, subtotal, shipping, "
                  "total, reserved_until, cancel_reason, attention_reason, paid_at, created_at, "
                  "updated_at")


# --- Lectura ------------------------------------------------------------------
def _items(cur: Any, tenant_id: str, order_id: str) -> list[dict[str, Any]]:
    cur.execute(
        "select item_id, sku, name, qty, unit_price, line_total from order_items "
        "where tenant_id = %s and order_id = %s order by name",
        (tenant_id, order_id),
    )
    return [{"item_id": str(r["item_id"]), "sku": r["sku"], "name": r["name"], "qty": r["qty"],
             "unit_price": float(r["unit_price"]), "line_total": float(r["line_total"])}
            for r in cur.fetchall()]


def _view(cur: Any, row: dict[str, Any]) -> dict[str, Any]:
    tenant_id, order_id = str(row["tenant_id"]), str(row["id"])
    cur.execute(
        "select provider, checkout_url, status from payments "
        "where tenant_id = %s and order_id = %s order by created_at desc limit 1",
        (tenant_id, order_id),
    )
    pay = cur.fetchone()
    return {
        "id": order_id, "number": row["number"], "status": row["status"],
        "status_label": STATUS_LABELS[row["status"]], "currency": row["currency"],
        "subtotal": float(row["subtotal"]), "shipping": float(row["shipping"]),
        "total": float(row["total"]),
        "reserved_until": row["reserved_until"].isoformat() if row["reserved_until"] else None,
        "cancel_reason": row["cancel_reason"], "attention_reason": row["attention_reason"],
        "paid_at": row["paid_at"].isoformat() if row["paid_at"] else None,
        "items": _items(cur, tenant_id, order_id),
        "payment": ({"provider": pay["provider"], "checkout_url": pay["checkout_url"],
                     "status": pay["status"]} if pay else None),
    }


def _fetch(cur: Any, tenant_id: str, order_id: str, lock: bool = False) -> Optional[dict[str, Any]]:
    cur.execute(
        f"select {_ORDER_COLUMNS} from orders where tenant_id = %s and id = %s"
        + (" for update" if lock else ""),
        (tenant_id, order_id),
    )
    return cur.fetchone()


def get_order(tenant_id: str, order_id: str) -> Optional[dict[str, Any]]:
    with tenant_tx(tenant_id) as cur:
        row = _fetch(cur, tenant_id, order_id)
        return _view(cur, row) if row else None


def _open_cart_row(cur: Any, tenant_id: str, conversation_id: str, lock: bool = False) -> Optional[dict[str, Any]]:
    cur.execute(
        f"select {_ORDER_COLUMNS} from orders "
        "where tenant_id = %s and conversation_id = %s and status = 'CART_OPEN'"
        + (" for update" if lock else ""),
        (tenant_id, conversation_id),
    )
    return cur.fetchone()


def get_cart(tenant_id: str, conversation_id: str) -> Optional[dict[str, Any]]:
    with tenant_tx(tenant_id) as cur:
        row = _open_cart_row(cur, tenant_id, conversation_id)
        return _view(cur, row) if row else None


def conversation_orders(tenant_id: str, conversation_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Pedidos ya confirmados (no carritos) de la conversación, el más reciente primero."""
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            f"select {_ORDER_COLUMNS} from orders where tenant_id = %s and conversation_id = %s "
            "and status <> 'CART_OPEN' order by created_at desc limit %s",
            (tenant_id, conversation_id, limit),
        )
        return [_view(cur, r) for r in cur.fetchall()]


# --- Carrito ------------------------------------------------------------------
@dataclass
class CartResult:
    status: str                    # ok | not_found | requires_human | no_price | insufficient_stock | not_in_cart
    cart: Optional[dict[str, Any]] = None
    offer: Optional[dict[str, Any]] = None
    available: int = 0


def _recompute(cur: Any, tenant_id: str, order_id: str) -> None:
    cur.execute(
        "update orders set subtotal = coalesce(t.s, 0), total = coalesce(t.s, 0) + shipping, "
        "updated_at = now() from (select sum(line_total) as s from order_items "
        "where tenant_id = %(t)s and order_id = %(o)s) t "
        "where orders.tenant_id = %(t)s and orders.id = %(o)s",
        {"t": tenant_id, "o": order_id},
    )


def _ensure_cart(cur: Any, tenant_id: str, conversation_id: str) -> dict[str, Any]:
    cur.execute(
        "insert into orders (tenant_id, conversation_id) values (%s, %s) "
        "on conflict (tenant_id, conversation_id) where status = 'CART_OPEN' do nothing",
        (tenant_id, conversation_id),
    )
    return _open_cart_row(cur, tenant_id, conversation_id, lock=True)


def add_item(tenant_id: str, conversation_id: str, item_id: str, qty: int = 1) -> CartResult:
    if qty <= 0:
        raise ValueError("la cantidad debe ser positiva")
    with tenant_tx(tenant_id) as cur:
        offer = inventory._offer_by_id(cur, tenant_id, item_id)
        if offer is None:
            return CartResult("not_found")
        if offer["pricing_mode"] != "fixed":
            return CartResult("requires_human", offer=offer)
        if offer["price"] is None:
            return CartResult("no_price", offer=offer)
        cart = _open_cart_row(cur, tenant_id, conversation_id, lock=True)
        current = None
        if cart is not None:
            cur.execute(
                "select qty from order_items where tenant_id = %s and order_id = %s and item_id = %s",
                (tenant_id, cart["id"], item_id),
            )
            current = cur.fetchone()
        new_qty = (current["qty"] if current else 0) + qty
        if new_qty > offer["available"]:
            return CartResult("insufficient_stock", cart=_view(cur, cart) if cart else None,
                              offer=offer, available=offer["available"])
        cart = cart or _ensure_cart(cur, tenant_id, conversation_id)
        cur.execute(
            "insert into order_items (tenant_id, order_id, item_id, sku, name, qty, unit_price, line_total) "
            "values (%(t)s, %(o)s, %(i)s, %(sku)s, %(name)s, %(q)s, %(p)s, %(q)s * %(p)s) "
            "on conflict (order_id, item_id) do update set qty = %(q)s, unit_price = %(p)s, "
            "line_total = %(q)s * %(p)s",
            {"t": tenant_id, "o": cart["id"], "i": item_id, "sku": offer["sku"],
             "name": offer["name"], "q": new_qty, "p": offer["price"]},
        )
        _recompute(cur, tenant_id, str(cart["id"]))
        return CartResult("ok", cart=_view(cur, _fetch(cur, tenant_id, str(cart["id"]))),
                          offer=offer, available=offer["available"])


def remove_item(tenant_id: str, conversation_id: str, item_id: str) -> CartResult:
    with tenant_tx(tenant_id) as cur:
        cart = _open_cart_row(cur, tenant_id, conversation_id, lock=True)
        if cart is None:
            return CartResult("not_in_cart")
        cur.execute(
            "delete from order_items where tenant_id = %s and order_id = %s and item_id = %s",
            (tenant_id, cart["id"], item_id),
        )
        if cur.rowcount == 0:
            return CartResult("not_in_cart", cart=_view(cur, cart))
        _recompute(cur, tenant_id, str(cart["id"]))
        return CartResult("ok", cart=_view(cur, _fetch(cur, tenant_id, str(cart["id"]))))


# --- Checkout -----------------------------------------------------------------
@dataclass
class CheckoutResult:
    status: str        # pending_payment | already_pending | price_changed | out_of_stock | empty | requires_human
    order: Optional[dict[str, Any]] = None
    price_changes: list[dict[str, Any]] = field(default_factory=list)
    shortage: Optional[dict[str, Any]] = None


def checkout(tenant_id: str, conversation_id: str) -> CheckoutResult:
    """Confirma el carrito: revalida, aparta stock (todo o nada) y deja el pedido esperando pago."""
    try:
        with tenant_tx(tenant_id) as cur:
            cart = _open_cart_row(cur, tenant_id, conversation_id, lock=True)
            if cart is None:
                # Doble confirmación: el carrito ya pasó a pendiente (lo bloqueó otra request).
                cur.execute(
                    f"select {_ORDER_COLUMNS} from orders where tenant_id = %s and conversation_id = %s "
                    "and status = 'PENDING_PAYMENT' order by created_at desc limit 1",
                    (tenant_id, conversation_id),
                )
                pending = cur.fetchone()
                if pending:
                    return CheckoutResult("already_pending", order=_view(cur, pending))
                return CheckoutResult("empty")
            order_id = str(cart["id"])
            items = _items(cur, tenant_id, order_id)
            if not items:
                return CheckoutResult("empty", order=_view(cur, cart))

            changes = []
            for it in items:
                offer = inventory._offer_by_id(cur, tenant_id, it["item_id"])
                if offer is None or offer["pricing_mode"] != "fixed" or offer["price"] is None:
                    return CheckoutResult("requires_human", order=_view(cur, cart),
                                          shortage={"name": it["name"]})
                if abs(offer["price"] - it["unit_price"]) > 0.005:
                    changes.append({"item_id": it["item_id"], "name": it["name"],
                                    "old": it["unit_price"], "new": offer["price"]})
                    cur.execute(
                        "update order_items set unit_price = %s, line_total = qty * %s "
                        "where tenant_id = %s and order_id = %s and item_id = %s",
                        (offer["price"], offer["price"], tenant_id, order_id, it["item_id"]),
                    )
            if changes:
                _recompute(cur, tenant_id, order_id)
                return CheckoutResult("price_changed",
                                      order=_view(cur, _fetch(cur, tenant_id, order_id)),
                                      price_changes=changes)

            inventory._reserve(cur, tenant_id, order_id,
                               [(it["item_id"], it["qty"]) for it in items])
            cur.execute(
                "update orders set status = 'PENDING_PAYMENT', updated_at = now(), "
                "reserved_until = now() + make_interval(mins => %s) "
                "where tenant_id = %s and id = %s",
                (settings.reservation_minutes, tenant_id, order_id),
            )
            return CheckoutResult("pending_payment", order=_view(cur, _fetch(cur, tenant_id, order_id)))
    except OutOfStock as exc:
        # La transacción ya hizo rollback: no quedó nada apartado.
        name = next((it["name"] for it in items if it["item_id"] == exc.item_id), exc.item_id)
        return CheckoutResult("out_of_stock", order=get_cart(tenant_id, conversation_id),
                              shortage={"item_id": exc.item_id, "name": name,
                                        "requested": exc.requested, "available": exc.available})


# --- Vencimientos y avance operativo --------------------------------------------
def _cancel_pending(cur: Any, tenant_id: str, order: dict[str, Any], reason: str) -> None:
    order_id = str(order["id"])
    inventory._release(cur, tenant_id, order_id,
                       [(it["item_id"], it["qty"]) for it in _items(cur, tenant_id, order_id)])
    cur.execute(
        "update orders set status = 'CANCELLED', cancel_reason = %s, updated_at = now() "
        "where tenant_id = %s and id = %s",
        (reason, tenant_id, order_id),
    )


def expire_reservations(limit: int = 100) -> int:
    """Libera el stock de pedidos impagos vencidos (todas las empresas).

    Una transacción POR pedido: cada liberación bloquea sus líneas en orden de item_id (igual que
    el checkout), así no hay ciclos de bloqueo con compras en curso ni con otro worker, y un pedido
    que falle no frena al resto. Idempotente: revalida el estado con el pedido bloqueado y salta
    los que otra transacción tiene tomados (skip locked)."""
    with system_tx() as cur:
        cur.execute(
            "select id, tenant_id from orders where status = 'PENDING_PAYMENT' "
            "and reserved_until < now() order by reserved_until limit %s",
            (limit,),
        )
        candidates = cur.fetchall()
    expired = 0
    for c in candidates:
        tenant_id = str(c["tenant_id"])
        try:
            with tenant_tx(tenant_id) as cur:
                cur.execute(
                    "select id from orders where tenant_id = %s and id = %s and status = 'PENDING_PAYMENT' "
                    "and reserved_until < now() for update skip locked",
                    (tenant_id, c["id"]),
                )
                row = cur.fetchone()
                if row is None:
                    continue
                _cancel_pending(cur, tenant_id, row, "reservation_expired")
                expired += 1
        except Exception:  # noqa: BLE001 - se registra y sigue con el resto
            log.exception("no se pudo vencer la reserva del pedido %s", c["id"])
    return expired


def advance_status(tenant_id: str, order_id: str, new_status: str) -> Optional[dict[str, Any]]:
    """Avance operativo (preparación/despacho/entrega) por parte del negocio."""
    with tenant_tx(tenant_id) as cur:
        return _advance(cur, tenant_id, order_id, new_status)


def _advance(cur: Any, tenant_id: str, order_id: str, new_status: str) -> Optional[dict[str, Any]]:
    row = _fetch(cur, tenant_id, order_id, lock=True)
    if row is None:
        return None
    if new_status not in FULFILLMENT_NEXT.get(row["status"], set()):
        raise ValueError(f"transición no permitida: {row['status']} → {new_status}")
    cur.execute(
        "update orders set status = %s, updated_at = now() where tenant_id = %s and id = %s",
        (new_status, tenant_id, order_id),
    )
    return _view(cur, _fetch(cur, tenant_id, order_id))
