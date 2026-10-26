"""Stock consistente bajo concurrencia + carrito/checkout (diseño §5).

Lo que tiene que valer siempre:
- nunca se aparta ni se vende más de lo que hay (lo garantiza la base, no sólo el código);
- N compras simultáneas de la última unidad ⇒ exactamente una gana;
- un pedido con varias líneas aparta todo o nada;
- precios que cambian antes de confirmar ⇒ se reconfirma, no se cobra el viejo.
"""
from __future__ import annotations

import threading

import psycopg
import pytest

from app.domain import inventory, orders

from conftest import TENANT_D, new_conversation, stock_of


def _cart(shop, *lines):
    conv = new_conversation(shop["tenant"])
    for key, qty in lines:
        assert orders.add_item(shop["tenant"], conv, shop[key], qty).status == "ok"
    return conv


def test_database_rejects_overselling_even_bypassing_the_app(shop, raw_conn):
    with raw_conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
        cur.execute("update stock_levels set reserved = on_hand + 1 where tenant_id = %s and item_id = %s",
                    (shop["tenant"], shop["last"]))
    raw_conn.rollback()
    with raw_conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
        cur.execute("update stock_levels set on_hand = -1 where tenant_id = %s and item_id = %s",
                    (shop["tenant"], shop["flex"]))
    raw_conn.rollback()


def test_twenty_concurrent_buyers_for_the_last_unit_exactly_one_wins(shop, raw_conn):
    convs = [_cart(shop, ("last", 1)) for _ in range(20)]   # agregar NO aparta
    barrier = threading.Barrier(len(convs))
    results: list[str] = []
    lock = threading.Lock()

    def buy(conv):
        barrier.wait()
        status = orders.checkout(shop["tenant"], conv).status
        with lock:
            results.append(status)

    threads = [threading.Thread(target=buy, args=(c,)) for c in convs]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert sorted(results) == ["out_of_stock"] * 19 + ["pending_payment"]
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 1)


def test_crossed_multi_item_checkouts_do_not_deadlock(shop, raw_conn):
    # Dos carritos con las mismas dos líneas: el apartado en orden de item_id evita deadlocks.
    convs = [_cart(shop, ("mono_aq", 1), ("flex", 2)), _cart(shop, ("flex", 2), ("mono_aq", 1))]
    barrier = threading.Barrier(2)
    results: list[str] = []

    def buy(conv):
        barrier.wait()
        results.append(orders.checkout(shop["tenant"], conv).status)

    threads = [threading.Thread(target=buy, args=(c,)) for c in convs]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert results == ["pending_payment", "pending_payment"]
    assert stock_of(raw_conn, shop["tenant"], shop["flex"]) == (40, 4)


def test_multi_item_reservation_is_all_or_nothing(shop, raw_conn):
    conv = _cart(shop, ("flex", 3), ("last", 1))
    # Otro cliente se lleva la última unidad antes de que este confirme.
    other = _cart(shop, ("last", 1))
    assert orders.checkout(shop["tenant"], other).status == "pending_payment"

    res = orders.checkout(shop["tenant"], conv)
    assert res.status == "out_of_stock"
    assert res.shortage["item_id"] == shop["last"] and res.shortage["available"] == 0
    assert stock_of(raw_conn, shop["tenant"], shop["flex"]) == (40, 0)   # no quedó apartado nada
    assert orders.get_cart(shop["tenant"], conv)["status"] == "CART_OPEN"


def test_add_to_cart_validates_stock_price_and_custom_items(shop):
    conv = new_conversation(shop["tenant"])
    assert orders.add_item(shop["tenant"], conv, shop["out"], 1).status == "insufficient_stock"
    res = orders.add_item(shop["tenant"], conv, shop["mono_hl"], 4)
    assert res.status == "insufficient_stock" and res.available == 3
    assert orders.add_item(shop["tenant"], conv, shop["custom"], 1).status == "requires_human"
    ok = orders.add_item(shop["tenant"], conv, shop["mono_hl"], 2)
    assert ok.status == "ok" and ok.cart["total"] == 258000
    # Sumar más de lo disponible en total también se rechaza.
    assert orders.add_item(shop["tenant"], conv, shop["mono_hl"], 2).status == "insufficient_stock"


def test_price_change_before_checkout_requires_reconfirmation(shop, raw_conn):
    conv = _cart(shop, ("mono_aq", 2))
    with raw_conn.cursor() as cur:
        cur.execute("insert into price_entries (tenant_id, item_id, amount, valid_from) "
                    "values (%s, %s, 95000, current_date)", (shop["tenant"], shop["mono_aq"]))
    raw_conn.commit()

    first = orders.checkout(shop["tenant"], conv)
    assert first.status == "price_changed"
    assert first.price_changes[0]["old"] == 89900 and first.price_changes[0]["new"] == 95000
    assert first.order["total"] == 190000
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (6, 0)   # todavía no aparta

    second = orders.checkout(shop["tenant"], conv)
    assert second.status == "pending_payment" and second.order["total"] == 190000


def test_double_checkout_does_not_duplicate(shop, raw_conn):
    conv = _cart(shop, ("flex", 1))
    first = orders.checkout(shop["tenant"], conv)
    again = orders.checkout(shop["tenant"], conv)
    assert first.status == "pending_payment" and again.status == "already_pending"
    assert again.order["id"] == first.order["id"]
    assert stock_of(raw_conn, shop["tenant"], shop["flex"]) == (40, 1)


def test_expired_reservation_releases_stock(shop, raw_conn):
    conv = _cart(shop, ("last", 1))
    order = orders.checkout(shop["tenant"], conv).order
    with raw_conn.cursor() as cur:
        cur.execute("update orders set reserved_until = now() - interval '1 minute' where id = %s",
                    (order["id"],))
    raw_conn.commit()

    assert orders.expire_reservations() >= 1
    expired = orders.get_order(shop["tenant"], order["id"])
    assert expired["status"] == "CANCELLED" and expired["cancel_reason"] == "reservation_expired"
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 0)
    # Repetir no vuelve a liberar (no hay doble descuento de `reserved`).
    orders.expire_reservations()
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 0)


def test_expiry_running_alongside_checkouts_keeps_stock_consistent(shop, raw_conn):
    # Pedidos vencidos con líneas cruzadas mientras otros clientes confirman las mismas líneas.
    stale = [_cart(shop, ("mono_aq", 1), ("flex", 1)), _cart(shop, ("flex", 1), ("mono_aq", 1))]
    for conv in stale:
        order = orders.checkout(shop["tenant"], conv).order
        with raw_conn.cursor() as cur:
            cur.execute("update orders set reserved_until = now() - interval '1 minute' where id = %s",
                        (order["id"],))
    raw_conn.commit()
    buyers = [_cart(shop, ("flex", 1), ("mono_aq", 1)) for _ in range(4)]
    barrier = threading.Barrier(len(buyers) + 1)
    results: list[str] = []
    errors: list[BaseException] = []

    def run(fn):
        barrier.wait()
        try:
            fn()
        except BaseException as exc:   # noqa: BLE001 - un deadlock aparecería acá
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(lambda c=c: results.append(orders.checkout(shop["tenant"], c).status),))
               for c in buyers]
    threads.append(threading.Thread(target=run, args=(orders.expire_reservations,)))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert errors == [] and results == ["pending_payment"] * 4
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (6, 4)
    assert stock_of(raw_conn, shop["tenant"], shop["flex"]) == (40, 4)


def test_orders_are_isolated_by_tenant(shop):
    conv = _cart(shop, ("flex", 1))
    order = orders.checkout(shop["tenant"], conv).order
    assert orders.get_order(TENANT_D, order["id"]) is None
    assert orders.get_cart(TENANT_D, conv) is None
    assert inventory.offers(TENANT_D, ids=[shop["flex"]]) == []


def test_fulfillment_transitions_are_restricted(shop):
    conv = _cart(shop, ("flex", 1))
    order = orders.checkout(shop["tenant"], conv).order
    with pytest.raises(ValueError):
        orders.advance_status(shop["tenant"], order["id"], "DISPATCHED")   # sin pago no se despacha


def test_restock_and_offer_availability(shop):
    assert inventory.restock(shop["tenant"], shop["out"], 2) == 2
    offer = inventory.offers(shop["tenant"], ids=[shop["out"]])[0]
    assert offer["available"] == 2 and offer["price"] == 59900
