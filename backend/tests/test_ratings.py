"""Encuesta de satisfacción: sólo el comprador dueño de la conversación califica su pedido PAGADO;
el dueño del negocio ve promedio e insatisfechos; otro negocio no ve nada."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import orders
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_inbox import HDR, _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _paid_order(client, shop):
    _, conv, token = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    return conv, token, order, pref


def test_buyer_rates_paid_order_and_owner_sees_unhappy(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Encuesta")
    conv, token, order, pref = _paid_order(client, shop)
    url = f"/public/{shop['slug']}/conversations/{conv}/orders/{order['id']}/rating"

    r = client.post(url, json={"score": 5}, headers={HDR: token})
    assert r.status_code == 400 and "pagado" in r.json()["detail"]          # todavía pendiente
    headers, body = SimulatedProvider().pay(pref, "approved")
    service.receive_notification("simulated", headers, {}, body)

    assert client.post(url, json={"score": 5}).status_code == 404                     # sin token
    assert client.post(url, json={"score": 5}, headers={HDR: "x" * 40}).status_code == 404
    for bad in (0, 6, "mucho", None):
        assert client.post(url, json={"score": bad}, headers={HDR: token}).status_code == 400
    r = client.post(url, json={"score": 2, "comment": "  Tardó mucho  " + "x" * 600}, headers={HDR: token})
    assert r.status_code == 200 and r.json()["score"] == 2 and len(r.json()["comment"]) == 500
    assert orders.get_order(shop["tenant"], order["id"])["rating"] == 2

    s = client.get("/app/insights?days=7", headers=bearer(shop["uid"])).json()["satisfaction"]
    assert s["count"] == 1 and s["average"] == 2 and s["unhappy"][0]["order_number"] == order["number"]
    # Corrige la calificación: sale de la lista de insatisfechos.
    assert client.post(url, json={"score": 5}, headers={HDR: token}).status_code == 200
    s = client.get("/app/insights?days=7", headers=bearer(shop["uid"])).json()["satisfaction"]
    assert s["count"] == 1 and s["average"] == 5 and s["unhappy"] == [] and s["satisfied_rate"] == 1

    other, _ = accounts("Otro Encuesta")
    assert client.get("/app/insights", headers=bearer(other)).json()["satisfaction"]["count"] == 0


def test_cannot_rate_order_of_another_conversation(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Encuesta 2")
    conv, token, order, pref = _paid_order(client, shop)
    headers, body = SimulatedProvider().pay(pref, "approved")
    service.receive_notification("simulated", headers, {}, body)
    _, conv2, token2 = _say(client, shop, "hola")      # otra persona, con SU token
    r = client.post(f"/public/{shop['slug']}/conversations/{conv2}/orders/{order['id']}/rating",
                    json={"score": 1}, headers={HDR: token2})
    assert r.status_code == 404


def test_rating_sends_webhook(accounts, raw_conn, monkeypatch):
    from app.domain import safe_http, webhooks
    monkeypatch.setattr(safe_http.socket, "getaddrinfo", lambda host, *_: [(0, 0, 0, "", ("93.184.216.34", 0))])
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Encuesta Webhook")
    client.post("/app/webhooks", headers=bearer(shop["uid"]),
                json={"url": "https://hooks.example/r", "events": ["order.rated"]})
    conv, token, order, pref = _paid_order(client, shop)
    headers, body = SimulatedProvider().pay(pref, "approved")
    service.receive_notification("simulated", headers, {}, body)
    client.post(f"/public/{shop['slug']}/conversations/{conv}/orders/{order['id']}/rating",
                json={"score": 4}, headers={HDR: token})
    d = client.get("/app/webhooks", headers=bearer(shop["uid"])).json()["deliveries"]
    assert [x["event"] for x in d] == ["order.rated"]
