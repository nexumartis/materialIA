"""Pagos: el pedido pasa a PAID sólo con el pago VERIFICADO del proveedor, una sola vez.

Proveedor simulado (mismo camino que Mercado Pago: aviso firmado → consulta del pago →
aplicación idempotente) y adaptador de Mercado Pago contra un transporte HTTP falso (no se
llama a Mercado Pago real)."""
from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.domain import orders
from app.main import app
from app.payments import providers, service
from app.payments.providers import MercadoPagoProvider, SimulatedProvider, sign_notification

from conftest import new_conversation, stock_of


def _pending_order(shop, key="last", qty=1):
    conv = new_conversation(shop["tenant"])
    assert orders.add_item(shop["tenant"], conv, shop[key], qty).status == "ok"
    order = orders.checkout(shop["tenant"], conv).order
    link = service.start_payment(shop["tenant"], order["id"])
    return conv, order, link["checkout_url"].rsplit("/", 1)[1]


def test_payment_link_is_created_once(shop):
    conv, order, pref = _pending_order(shop)
    again = service.start_payment(shop["tenant"], order["id"])
    assert again["checkout_url"].endswith(pref) and again["provider"] == "simulated"


def test_approved_payment_marks_paid_and_sells_stock_once(shop, raw_conn):
    conv, order, pref = _pending_order(shop)
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body) == (200, "pedido pagado")
    # El proveedor reintenta el mismo aviso: no descuenta dos veces.
    assert service.receive_notification("simulated", headers, {}, body) == (200, "ya estaba pagado")

    paid = orders.get_order(shop["tenant"], order["id"])
    assert paid["status"] == "PAID" and paid["paid_at"]
    assert paid["payment"]["status"] == "approved"
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (0, 0)
    # El cliente recibe la confirmación en su conversación y el CRM registra la venta.
    with raw_conn.cursor() as cur:
        cur.execute("select content from messages where conversation_id = %s and direction = 'outbound'",
                    (conv,))
        notes = [r["content"] for r in cur.fetchall() if "Pago confirmado" in r["content"]]
        # Sin promesa de aviso que el sistema no envía: indica cómo consultar el estado.
        assert notes and "Te aviso" not in notes[0] and "¿cómo va mi pedido?" in notes[0]
        cur.execute("select stage from opportunities where conversation_id = %s", (conv,))
        assert cur.fetchone()["stage"] == "cerrada"
    raw_conn.commit()


def test_invalid_signature_is_rejected_and_changes_nothing(shop, raw_conn):
    conv, order, pref = _pending_order(shop)
    headers, body = SimulatedProvider().pay(pref, "approved")
    forged = sign_notification("otra-clave", body["data"]["id"], headers["x-request-id"])
    assert service.receive_notification("simulated", forged, {}, body)[0] == 401
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PENDING_PAYMENT"
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 1)


def test_unknown_payment_id_does_not_pay_anything(shop):
    conv, order, pref = _pending_order(shop)
    fake_id = "00000000-0000-0000-0000-000000000123"
    headers = sign_notification(settings.sim_webhook_secret, fake_id, "req-1")
    body = {"type": "payment", "data": {"id": fake_id}}
    assert service.receive_notification("simulated", headers, {}, body) == (200, "pago inexistente en el proveedor")
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PENDING_PAYMENT"


def test_rejected_payment_keeps_order_waiting(shop, raw_conn):
    conv, order, pref = _pending_order(shop)
    headers, body = SimulatedProvider().pay(pref, "rejected")
    status, outcome = service.receive_notification("simulated", headers, {}, body)
    assert status == 200 and "rejected" in outcome
    still = orders.get_order(shop["tenant"], order["id"])
    assert still["status"] == "PENDING_PAYMENT" and still["payment"]["status"] == "rejected"
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 1)


def test_amount_mismatch_is_flagged_not_paid(shop, raw_conn):
    conv, order, pref = _pending_order(shop)
    with raw_conn.cursor() as cur:
        cur.execute("insert into sim_provider_payments (preference_id, external_ref, status, amount) "
                    "values (%s, %s, 'approved', 1) returning id", (pref, order["id"]))
        pid = str(cur.fetchone()["id"])
    raw_conn.commit()
    headers = sign_notification(settings.sim_webhook_secret, pid, "req-2")
    status, outcome = service.receive_notification("simulated", headers, {}, {"type": "payment", "data": {"id": pid}})
    assert status == 200 and "requiere revisión" in outcome
    flagged = orders.get_order(shop["tenant"], order["id"])
    assert flagged["status"] == "PENDING_PAYMENT" and flagged["attention_reason"] == "amount_mismatch"


def _expire(raw_conn, order_id):
    with raw_conn.cursor() as cur:
        cur.execute("update orders set reserved_until = now() - interval '1 minute' where id = %s", (order_id,))
    raw_conn.commit()
    orders.expire_reservations()


def test_late_payment_with_stock_still_available_is_honored(shop, raw_conn):
    conv, order, pref = _pending_order(shop, key="flex", qty=2)
    _expire(raw_conn, order["id"])
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PAID"
    assert stock_of(raw_conn, shop["tenant"], shop["flex"]) == (38, 0)


def test_late_payment_without_stock_is_flagged_never_oversold(shop, raw_conn):
    conv, order, pref = _pending_order(shop, key="last")
    _expire(raw_conn, order["id"])
    _pending_order(shop, key="last")          # otro cliente aparta la última unidad
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pagado sin stock: requiere devolución"
    late = orders.get_order(shop["tenant"], order["id"])
    assert late["status"] == "CANCELLED" and late["attention_reason"] == "paid_without_stock"
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 1)   # sólo el otro pedido


def test_simulated_checkout_page_and_webhook_route(shop):
    conv, order, pref = _pending_order(shop)
    client = TestClient(app)
    page = client.get(f"/sandbox/checkout/{pref}")
    assert page.status_code == 200 and "SIMULADO" in page.text
    paid = client.post(f"/sandbox/checkout/{pref}/pay?outcome=approved")
    assert paid.status_code == 200 and "Pago aprobado" in paid.text
    # Ruta pública del webhook: sin firma válida => 401.
    resp = client.post("/webhooks/simulated?type=payment&data.id=x", json={"type": "payment", "data": {"id": "x"}})
    assert resp.status_code == 401


# --- Mercado Pago (adaptador) contra un transporte HTTP falso ------------------------
def _mp_client(store: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer TEST-token"
        if request.method == "POST" and request.url.path == "/checkout/preferences":
            store["preference"] = json.loads(request.content)
            store["idempotency"] = request.headers.get("X-Idempotency-Key")
            return httpx.Response(201, json={"id": "pref-123", "init_point": "https://mp.test/checkout/pref-123"})
        if request.method == "GET" and request.url.path == "/v1/payments/987":
            return httpx.Response(200, json={"id": 987, "status": "approved",
                                             "external_reference": store["order_id"],
                                             "transaction_amount": store["amount"], "currency_id": "ARS"})
        return httpx.Response(404, json={})
    return httpx.Client(base_url="https://api.mp.test", transport=httpx.MockTransport(handler))


def test_mercadopago_adapter_end_to_end_with_fake_transport(shop, raw_conn, monkeypatch):
    monkeypatch.setattr(settings, "payment_provider", "mercadopago")
    monkeypatch.setattr(settings, "mp_access_token", "TEST-token")
    monkeypatch.setattr(settings, "mp_webhook_secret", "mp-secret")
    store: dict = {}
    client = _mp_client(store)
    monkeypatch.setattr(service, "get_provider", lambda name=None: MercadoPagoProvider(client=client))

    conv = new_conversation(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["mono_aq"], 2)
    order = orders.checkout(shop["tenant"], conv).order
    link = service.start_payment(shop["tenant"], order["id"])
    assert link == {"provider": "mercadopago", "checkout_url": "https://mp.test/checkout/pref-123"}
    pref = store["preference"]
    assert pref["external_reference"] == order["id"]
    assert pref["items"][0]["quantity"] == 2 and pref["items"][0]["unit_price"] == 89900
    assert pref["notification_url"].endswith("/webhooks/mercadopago")
    assert store["idempotency"] == f"order-{order['id']}"

    store.update(order_id=order["id"], amount=179800)
    headers = sign_notification("mp-secret", "987", "req-mp")
    status, outcome = service.receive_notification(
        "mercadopago", headers, {"type": "payment", "data.id": "987"}, {"type": "payment", "data": {"id": "987"}})
    assert (status, outcome) == (200, "pedido pagado")
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (4, 0)


def test_mercadopago_signature_verification():
    headers = sign_notification("s3cret", "ABC123", "req-9", ts="1704908010")
    assert providers.verify_signature("s3cret", headers, "ABC123")
    assert not providers.verify_signature("s3cret", headers, "OTRO")
    assert not providers.verify_signature("otra", headers, "ABC123")
    assert not providers.verify_signature(None, headers, "ABC123")
    assert not providers.verify_signature("s3cret", {"x-request-id": "req-9"}, "ABC123")


def test_mercadopago_requires_test_credentials(monkeypatch):
    monkeypatch.setattr(settings, "mp_access_token", None)
    try:
        MercadoPagoProvider()
    except providers.PaymentProviderError as exc:
        assert "MP_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("debería exigir credenciales")


def test_second_approved_payment_is_flagged_for_refund(shop):
    conv, order, pref = _pending_order(shop)
    sim = SimulatedProvider()
    h1, b1 = sim.pay(pref, "approved")
    assert service.receive_notification("simulated", h1, {}, b1)[1] == "pedido pagado"
    h2, b2 = sim.pay(pref, "approved")                 # el comprador pagó dos veces
    assert service.receive_notification("simulated", h2, {}, b2)[1] == "pago duplicado: requiere devolución"
    paid = orders.get_order(shop["tenant"], order["id"])
    assert paid["status"] == "PAID" and paid["attention_reason"] == "duplicate_payment"


def test_retry_after_rejection_uses_the_same_link(shop, raw_conn):
    conv, order, pref = _pending_order(shop)
    sim = SimulatedProvider()
    h, b = sim.pay(pref, "rejected")
    service.receive_notification("simulated", h, {}, b)
    again = service.start_payment(shop["tenant"], order["id"])
    assert again["checkout_url"].endswith(pref)
    h, b = sim.pay(pref, "approved")
    assert service.receive_notification("simulated", h, {}, b)[1] == "pedido pagado"
    with raw_conn.cursor() as cur:
        cur.execute("select status from payments where order_id = %s order by created_at", (order["id"],))
        assert sorted(r["status"] for r in cur.fetchall()) == ["approved", "rejected"]
    raw_conn.commit()


def test_simulated_checkout_is_disabled_when_mercadopago_is_configured(shop, monkeypatch):
    conv, order, pref = _pending_order(shop)
    monkeypatch.setattr(settings, "payment_provider", "mercadopago")
    client = TestClient(app)
    assert client.get(f"/sandbox/checkout/{pref}").status_code == 404
    assert client.post(f"/sandbox/checkout/{pref}/pay?outcome=approved").status_code == 404
    headers = sign_notification(settings.sim_webhook_secret, "x", "r")
    assert service.receive_notification("simulated", headers, {}, {"type": "payment", "data": {"id": "x"}})[0] == 404
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "PENDING_PAYMENT"


def test_signature_manifest_omits_missing_parts():
    assert providers._manifest("ABC", "", "123") == "id:abc;ts:123;"
    assert providers._manifest("abc", "req", "123") == "id:abc;request-id:req;ts:123;"


def test_correct_payment_after_amount_mismatch_fulfils_the_order(shop, raw_conn):
    conv, order, pref = _pending_order(shop)
    with raw_conn.cursor() as cur:
        cur.execute("insert into sim_provider_payments (preference_id, external_ref, status, amount) "
                    "values (%s, %s, 'approved', 1) returning id", (pref, order["id"]))
        bad = str(cur.fetchone()["id"])
    raw_conn.commit()
    h = sign_notification(settings.sim_webhook_secret, bad, "req-bad")
    service.receive_notification("simulated", h, {}, {"type": "payment", "data": {"id": bad}})
    h, b = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", h, {}, b)[1] == "pedido pagado"
    paid = orders.get_order(shop["tenant"], order["id"])
    assert paid["status"] == "PAID" and paid["attention_reason"] is None


def test_late_payment_retried_after_restock_clears_attention(shop, raw_conn):
    from app.domain import inventory
    conv, order, pref = _pending_order(shop, key="last")
    _expire(raw_conn, order["id"])
    _pending_order(shop, key="last")
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pagado sin stock: requiere devolución"
    inventory.restock(shop["tenant"], shop["last"], 1)
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    paid = orders.get_order(shop["tenant"], order["id"])
    assert paid["status"] == "PAID" and paid["attention_reason"] is None
    assert stock_of(raw_conn, shop["tenant"], shop["last"]) == (1, 1)
