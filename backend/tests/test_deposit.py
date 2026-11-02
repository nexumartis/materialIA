"""Seña para productos a pedido: el dueño cotiza, se cobra la seña y después el saldo, cada uno
con pago verificado. Un pedido a medida no toca stock. Un comprobante nunca acredita nada."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import orders
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def shop(client, accounts, raw_conn):
    s = _shop(client, accounts, raw_conn, "Tienda Seña")
    with raw_conn.cursor() as cur:
        cur.execute("select id from catalog_items where tenant_id = %s and sku = 'INO-1'", (s["tenant"],))
        s["custom"] = str(cur.fetchone()["id"])
    raw_conn.commit()
    return s


def _quote(client, shop, conv, deposit=30000, price=100000, qty=1, item=None):
    return client.post(f"/app/inbox/{conv}/quote", headers=bearer(shop["uid"]), json={
        "lines": [{"item_id": item or shop["custom"], "qty": qty, "unit_price": price}], "deposit": deposit})


def _pay_link(text):
    return text.rsplit("/", 1)[1].split()[0]


def _pay(pref, outcome="approved"):
    headers, body = SimulatedProvider().pay(pref, outcome)
    return service.receive_notification("simulated", headers, {}, body)


def _last_bot(shop, conv):
    with service.tenant_tx(shop["tenant"]) as cur:
        cur.execute("select content from messages where tenant_id = %s and conversation_id = %s "
                    "and direction = 'outbound' order by created_at desc limit 1", (shop["tenant"], conv))
        return cur.fetchone()["content"]


def test_deposit_then_balance_each_verified(client, shop):
    _, conv, _ = _say(client, shop, "quiero el inodoro a pedido")
    r = _quote(client, shop, conv)
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["status"] == "PENDING_PAYMENT" and order["deposit"] == 30000 and order["amount_due"] == 30000
    msg = _last_bot(shop, conv)
    assert "seña de $30.000,00" in msg and "Total $100.000,00" in msg
    pref = _pay_link(msg)

    assert _pay(pref) == (200, service.DEPOSIT_OK)
    o = orders.get_order(shop["tenant"], order["id"])
    assert o["status"] == "DEPOSIT_PAID" and o["amount_due"] == 70000 and o["receipt_id"] is None
    balance = _last_bot(shop, conv)
    assert "saldo de $70.000,00" in balance
    balance_pref = _pay_link(balance)
    assert balance_pref != pref
    assert _pay(balance_pref) == (200, "pedido pagado")
    o = orders.get_order(shop["tenant"], order["id"])
    assert o["status"] == "PAID" and o["receipt_id"] and o["amount_due"] == 0


def test_replayed_deposit_notification_is_not_the_balance(client, shop):
    _, conv, _ = _say(client, shop, "hola")
    order = _quote(client, shop, conv, deposit=50000).json()      # seña = saldo: el caso ambiguo
    pref = _pay_link(_last_bot(shop, conv))
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body) == (200, service.DEPOSIT_OK)
    assert service.receive_notification("simulated", headers, {}, body) == (200, "seña ya acreditada")
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "DEPOSIT_PAID"


def test_transfer_must_match_deposit_or_total_and_balance_after(client, shop):
    _, conv, _ = _say(client, shop, "hola")
    order = _quote(client, shop, conv).json()
    h = bearer(shop["uid"])
    url = f"/app/orders/{order['id']}/confirm-transfer"
    r = client.post(url, headers=h, json={"reference": "BCO-S1", "amount": 1234, "currency": "ARS"})
    assert r.status_code == 400 and "30000.00 o 100000.00" in r.json()["detail"]
    r = client.post(url, headers=h, json={"reference": "BCO-S1", "amount": 30000, "currency": "ARS"})
    assert r.status_code == 200 and r.json()["order"]["status"] == "DEPOSIT_PAID"
    r = client.post(url, headers=h, json={"reference": "BCO-S2", "amount": 30000, "currency": "ARS"})
    assert r.status_code == 400                         # señado: sólo el saldo
    r = client.post(url, headers=h, json={"reference": "BCO-S2", "amount": 70000, "currency": "ARS"})
    assert r.status_code == 200 and r.json()["order"]["status"] == "PAID"


def test_full_payment_at_once_and_no_stock_touched(client, shop, raw_conn):
    _, conv, _ = _say(client, shop, "hola")
    order = _quote(client, shop, conv, deposit=None, qty=2, price=5000).json()
    assert order["deposit"] is None and order["amount_due"] == 10000
    assert _pay(_pay_link(_last_bot(shop, conv))) == (200, "pedido pagado")
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) as n from stock_movements where tenant_id = %s and order_id = %s",
                    (shop["tenant"], order["id"]))
        assert cur.fetchone()["n"] == 0
    raw_conn.commit()


def test_quote_validation_and_permissions(client, shop, accounts):
    _, conv, _ = _say(client, shop, "hola")
    assert _quote(client, shop, conv, deposit=100000).status_code == 400       # seña = total
    assert _quote(client, shop, conv, deposit=0).status_code == 400
    assert _quote(client, shop, conv, price=0).status_code == 400
    r = _quote(client, shop, conv, item=shop["item"])                          # con stock: lo vende el agente
    assert r.status_code == 400 and "a pedido" in r.json()["detail"]
    other, _ = accounts("Otra Seña")
    r = client.post(f"/app/inbox/{conv}/quote", headers=bearer(other),
                    json={"lines": [{"item_id": shop["custom"], "qty": 1, "unit_price": 1}]})
    assert r.status_code == 404


def test_refunded_deposit_needs_a_person(client, shop):
    _, conv, _ = _say(client, shop, "hola")
    order = _quote(client, shop, conv).json()
    pref = _pay_link(_last_bot(shop, conv))
    assert _pay(pref) == (200, service.DEPOSIT_OK)
    from app.payments.providers import ProviderPayment
    with service.tenant_tx(shop["tenant"]) as cur:
        cur.execute("select provider_payment_id from payments where tenant_id = %s and order_id = %s "
                    "and status = 'approved'", (shop["tenant"], order["id"]))
        pid = cur.fetchone()["provider_payment_id"]
    service.apply_payment("simulated", ProviderPayment(pid, "refunded", order["id"], 30000, "ARS"))
    o = orders.get_order(shop["tenant"], order["id"])
    assert o["status"] == "REFUNDED" and o["attention_reason"] == "payment_refunded"


def _paid_with_deposit(client, shop):
    _, conv, token = _say(client, shop, "hola")
    order = _quote(client, shop, conv).json()
    assert _pay(_pay_link(_last_bot(shop, conv))) == (200, service.DEPOSIT_OK)
    balance_pref = _pay_link(_last_bot(shop, conv))
    assert _pay(balance_pref) == (200, "pedido pagado")
    return conv, token, order, balance_pref


def test_second_balance_payment_is_flagged_duplicate(client, shop):
    _, _, order, balance_pref = _paid_with_deposit(client, shop)
    assert _pay(balance_pref) == (200, "pago duplicado: requiere devolución")
    assert orders.get_order(shop["tenant"], order["id"])["attention_reason"] == "duplicate_payment"


def test_partial_refund_keeps_order_and_receipt_lists_both_payments(client, shop):
    from app.domain import receipts
    from app.payments.providers import ProviderPayment
    _, _, order, _ = _paid_with_deposit(client, shop)
    with service.tenant_tx(shop["tenant"]) as cur:
        r = receipts.get(cur, shop["tenant"], order["id"])
        cur.execute("select provider_payment_id from payments where tenant_id = %s and order_id = %s "
                    "and charge = 'deposit'", (shop["tenant"], order["id"]))
        deposit_pid = cur.fetchone()["provider_payment_id"]
    assert [(p["concept"], p["amount"]) for p in r["payments"]] == [("Seña", 30000), ("Saldo", 70000)]
    assert receipts.render_pdf(r).startswith(b"%PDF")
    service.apply_payment("simulated", ProviderPayment(deposit_pid, "refunded", order["id"], 30000, "ARS"))
    o = orders.get_order(shop["tenant"], order["id"])
    assert o["status"] == "PAID" and o["attention_reason"] == "payment_refunded"


def test_late_deposit_on_expired_quote_is_accepted(client, shop, raw_conn):
    _, conv, _ = _say(client, shop, "hola")
    order = _quote(client, shop, conv).json()
    with raw_conn.cursor() as cur:
        cur.execute("update orders set reserved_until = now() - interval '1 minute' where id = %s", (order["id"],))
    raw_conn.commit()
    assert orders.expire_reservations() >= 1
    r = client.post(f"/app/orders/{order['id']}/confirm-transfer", headers=bearer(shop["uid"]),
                    json={"reference": "BCO-LATE", "amount": 30000, "currency": "ARS"})
    assert r.status_code == 200 and r.json()["order"]["status"] == "DEPOSIT_PAID"


def test_invalid_item_id_is_400_and_status_reply_offers_balance(client, shop):
    _, conv, token = _say(client, shop, "hola")
    r = client.post(f"/app/inbox/{conv}/quote", headers=bearer(shop["uid"]),
                    json={"lines": [{"item_id": "abc", "qty": 1, "unit_price": 10}]})
    assert r.status_code == 400
    _quote(client, shop, conv)
    assert _pay(_pay_link(_last_bot(shop, conv))) == (200, service.DEPOSIT_OK)
    j, _, _ = _say(client, shop, "como va mi pedido?", conv, token)
    assert "señado" in j["reply"] and "70.000" in j["reply"] and "seguimiento" not in j["reply"]
