"""Transferencia verificada por el dueño y constancia comercial de compra (T2 de comprobantes).

La transferencia la acredita el DUEÑO (nunca un archivo): mismo efecto que un pago verificado del
proveedor. Una constancia y un aviso por pedido, en la misma transacción que lo deja PAID."""
from __future__ import annotations

import threading

import pytest

from app.domain import opportunities, orders, receipts
from app.payments import service
from app.payments.providers import SimulatedProvider

from conftest import new_conversation, stock_of


@pytest.fixture
def owner(shop, accounts, raw_conn):
    uid, _ = accounts()
    with raw_conn.cursor() as cur:   # dueño del negocio de prueba (una persona = un negocio)
        cur.execute("update memberships set tenant_id = %s where user_id = %s", (shop["tenant"], uid))
    raw_conn.commit()
    return uid


def _pending(shop, key="last", qty=1):
    conv = new_conversation(shop["tenant"])
    assert orders.add_item(shop["tenant"], conv, shop[key], qty).status == "ok"
    return conv, orders.checkout(shop["tenant"], conv).order


def _counts(raw_conn, order_id, conv):
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) n from receipts where order_id = %s", (order_id,))
        n_receipts = cur.fetchone()["n"]
        cur.execute("select payload->>'type' t, count(*) n from messages where conversation_id = %s "
                    "and payload ? 'type' group by 1", (conv,))
        msgs = {r["t"]: r["n"] for r in cur.fetchall()}
    raw_conn.commit()
    return n_receipts, msgs


def _receipt(shop, order_id):
    from app.db import tenant_tx
    with tenant_tx(shop["tenant"]) as cur:
        return receipts.get(cur, shop["tenant"], order_id)


def test_transfer_confirmed_by_owner_pays_once_with_one_receipt(shop, owner, raw_conn):
    conv, order = _pending(shop)
    args = (shop["tenant"], owner, order["id"], " trx 0099-ab ", order["total"], "ars")
    assert service.confirm_transfer(*args) == "pedido pagado"
    assert service.confirm_transfer(*args) == "ya estaba pagado"          # doble clic
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PAID"
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (0, 0)
    assert _counts(raw_conn, order["id"], conv) == (1, {"receipt": 1})

    snap = _receipt(shop, order["id"])
    assert snap["legend"] == "Constancia comercial de compra — no es factura fiscal"
    assert snap["business"] == "Sanitarios Test (SINTÉTICA)" and snap["order_number"] == order["number"]
    assert [(i["sku"], i["qty"]) for i in snap["items"]] == [("T-COC-2LL-NEG", 1)]
    assert snap["total"] == order["total"] and snap["currency"] == "ARS"
    assert snap["payment"] == {"origin": "Transferencia verificada por el negocio", "reference": "TRX0099-AB",
                               "amount": order["total"], "currency": "ARS"}
    with raw_conn.cursor() as cur:   # actor y fecha auditados
        cur.execute("select verified_by, verified_at from payments where order_id = %s", (order["id"],))
        pay = cur.fetchone()
        cur.execute("select metadata_redacted m from audit_events where event_type = 'transfer_confirmed' "
                    "and entity_id = %s", (order["id"],))
        audits = [r["m"] for r in cur.fetchall()]
    raw_conn.commit()
    assert str(pay["verified_by"]) == owner and pay["verified_at"]
    assert len(audits) == 2 and audits[0]["actor"] == owner and audits[0]["reference"] == "TRX0099-AB"


def test_concurrent_confirmations_issue_a_single_receipt(shop, owner, raw_conn):
    conv, order = _pending(shop)
    results, barrier = [], threading.Barrier(4)

    def confirm(ref):
        barrier.wait()
        try:
            results.append(service.confirm_transfer(shop["tenant"], owner, order["id"], ref,
                                                    order["total"], "ARS"))
        except service.ReferenceInUse as exc:
            results.append(str(exc))
    threads = [threading.Thread(target=confirm, args=(ref,)) for ref in ("REF-1", "REF-1", "REF-1", "REF-1")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["pedido pagado", "ya estaba pagado", "ya estaba pagado", "ya estaba pagado"]
    assert _counts(raw_conn, order["id"], conv) == (1, {"receipt": 1})
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (0, 0)


def test_repeated_webhook_and_failing_after_effects_keep_one_receipt(shop, raw_conn, monkeypatch):
    conv, order = _pending(shop)
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")

    def boom(*_, **__):
        raise RuntimeError("CRM caído")
    monkeypatch.setattr(opportunities, "audit", boom)   # _after_paid falla después del commit
    assert service.receive_notification("simulated", headers, {}, body) == (200, "pedido pagado")
    assert service.receive_notification("simulated", headers, {}, body) == (200, "ya estaba pagado")
    assert _counts(raw_conn, order["id"], conv) == (1, {"receipt": 1})
    assert _receipt(shop, order["id"])["payment"]["origin"] == "Pago simulado (entorno de prueba)"


def test_reference_already_used_in_another_order_is_rejected_and_touches_nothing(shop, owner, raw_conn):
    conv_a, a = _pending(shop, key="flex")
    conv_b, b = _pending(shop, key="alt")
    service.confirm_transfer(shop["tenant"], owner, a["id"], "BANCO-777", a["total"], "ARS")
    with pytest.raises(service.ReferenceInUse):
        service.confirm_transfer(shop["tenant"], owner, b["id"], "banco-777", b["total"], "ARS")
    assert orders.get_order(shop["tenant"], a["id"])["status"] == "PAID"
    still = orders.get_order(shop["tenant"], b["id"])
    assert still["status"] == "PENDING_PAYMENT" and still["payment"] is None
    assert _counts(raw_conn, b["id"], conv_b) == (0, {})
    assert stock_of(raw_conn, shop["tenant"], shop["alt"]) == (8, 1)


@pytest.mark.parametrize("amount_delta, currency", [(-100, "ARS"), (0, "USD")], ids=["importe", "moneda"])
def test_wrong_amount_or_currency_never_pays_and_notifies_once(shop, owner, raw_conn, amount_delta, currency):
    conv, order = _pending(shop)
    for _ in range(2):
        outcome = service.confirm_transfer(shop["tenant"], owner, order["id"], "REF-MAL",
                                           order["total"] + amount_delta, currency)
        assert outcome == "monto o moneda no coinciden: requiere revisión"
    flagged = orders.get_order(shop["tenant"], order["id"])
    assert flagged["status"] == "PENDING_PAYMENT" and flagged["attention_reason"] == "amount_mismatch"
    assert _counts(raw_conn, order["id"], conv) == (0, {"payment_attention": 1})


def test_late_transfer_without_stock_has_no_receipt_and_notifies_once(shop, owner, raw_conn):
    conv, order = _pending(shop, key="last")
    with raw_conn.cursor() as cur:
        cur.execute("update orders set reserved_until = now() - interval '1 minute' where id = %s", (order["id"],))
    raw_conn.commit()
    orders.expire_reservations()
    _pending(shop, key="last")                       # otro cliente aparta la última unidad
    for _ in range(2):
        assert (service.confirm_transfer(shop["tenant"], owner, order["id"], "REF-TARDE", order["total"], "ARS")
                == "pagado sin stock: requiere devolución")
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "CANCELLED"
    assert _counts(raw_conn, order["id"], conv) == (0, {"payment_attention": 1})


def test_reversal_keeps_the_receipt_and_marks_the_payment(shop, raw_conn):
    conv, order = _pending(shop)
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    sim = SimulatedProvider()
    headers, body = sim.pay(pref, "approved")
    service.receive_notification("simulated", headers, {}, body)
    pid = body["data"]["id"]
    with raw_conn.cursor() as cur:
        cur.execute("update sim_provider_payments set status = 'refunded' where id = %s", (pid,))
    raw_conn.commit()
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pago refunded"
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "REFUNDED"
    assert _counts(raw_conn, order["id"], conv) == (1, {"receipt": 1})   # sin aviso de "revisión"
    with raw_conn.cursor() as cur:
        cur.execute("select reversed_at, verified_at from payments where order_id = %s", (order["id"],))
        pay = cur.fetchone()
    raw_conn.commit()
    assert pay["reversed_at"] and pay["verified_at"]


def test_revoked_membership_or_other_business_cannot_confirm(shop, owner, accounts, raw_conn):
    conv, order = _pending(shop)
    stranger, other_tenant = accounts("Otro negocio")
    with pytest.raises(PermissionError):
        service.confirm_transfer(shop["tenant"], stranger, order["id"], "REF-X", order["total"], "ARS")
    with pytest.raises(LookupError):   # el pedido no es del negocio del que confirma
        service.confirm_transfer(other_tenant, stranger, order["id"], "REF-X", order["total"], "ARS")
    with raw_conn.cursor() as cur:
        cur.execute("delete from memberships where user_id = %s", (owner,))
    raw_conn.commit()
    with pytest.raises(PermissionError):
        service.confirm_transfer(shop["tenant"], owner, order["id"], "REF-X", order["total"], "ARS")
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PENDING_PAYMENT"
    assert _counts(raw_conn, order["id"], conv) == (0, {})


@pytest.mark.parametrize("ref, amount", [("", 100), ("ab", 100), ("REF;DROP", 100), ("REF-OK", 0)])
def test_invalid_transfer_data_is_rejected(shop, owner, ref, amount):
    conv, order = _pending(shop)
    with pytest.raises(ValueError):
        service.confirm_transfer(shop["tenant"], owner, order["id"], ref, amount, "ARS")
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PENDING_PAYMENT"
