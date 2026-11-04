"""Reparto e instalación: se agenda la entrega de un pedido pagado con envío; el repartidor (rol
«driver») ve SÓLO su hoja de ruta, no el panel; cada paso avisa al cliente en su charla y avanza el
pedido hasta «entregado»; otro repartidor u otro negocio no tocan nada."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import auth, buyer_session
from app.domain import orders, reparto
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop
from test_team import _email, signup  # noqa: F401  (fixture)

ADDRESS = {"calle": "Av. Mitre", "altura": "1234", "localidad": "Avellaneda", "texto": "Av. Mitre 1234, Avellaneda"}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


def _paid_delivery(shop, raw_conn):
    conv, token = buyer_session.start(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    with raw_conn.cursor() as cur:
        cur.execute("update orders set delivery_method = 'delivery', delivery_address = %s::jsonb, "
                    "delivery_contact = %s::jsonb where id = %s",
                    (json.dumps(ADDRESS), json.dumps({"name": "Ana", "phone": "1155550000"}), order["id"]))
    raw_conn.commit()
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    return conv, token, order


def _driver(client, shop, signup):
    email = _email()
    assert client.post("/app/team/invites", headers=bearer(shop["uid"]), json={"email": email, "role": "driver"}).status_code == 200
    return signup(email)


def _history(client, shop, conv, token):
    r = client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={"X-Conversation-Token": token})
    return [m["content"] for m in r.json()["messages"]]


def test_driver_cannot_enter_the_panel(client, accounts, raw_conn, signup):
    shop = _shop(client, accounts, raw_conn, "Reparto Permisos")
    uid = _driver(client, shop, signup)
    h = bearer(uid)
    assert client.get("/app/me", headers=h).json()["role"] == "driver"
    for path in ("/app/orders", "/app/opportunities", "/app/catalog", "/app/deliveries", "/app/alerts"):
        assert client.get(path, headers=h).status_code == 403, path
    assert client.get("/app/route", headers=h).json()["jobs"] == []
    assert client.post("/app/team/invites", headers=bearer(shop["uid"]),
                       json={"email": _email(), "role": "admin"}).status_code == 400


def test_full_delivery_flow_notifies_customer_and_advances_order(client, accounts, raw_conn, signup):
    shop = _shop(client, accounts, raw_conn, "Reparto Flujo")
    driver = _driver(client, shop, signup)
    conv, token, order = _paid_delivery(shop, raw_conn)
    owner = bearer(shop["uid"])
    board = client.get("/app/deliveries", headers=owner).json()
    assert [p["order_id"] for p in board["pending"]] == [order["id"]]
    assert driver in [d["user_id"] for d in board["drivers"]]
    job = client.post("/app/deliveries", headers=owner, json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "am",
        "kind": "delivery_install", "assigned_to": driver, "note": "Tercer piso, sin ascensor"}).json()
    assert job["status"] == "scheduled"
    assert "hoy" in _history(client, shop, conv, token)[-1]
    assert client.post("/app/deliveries", headers=owner, json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "pm"}).status_code == 400

    h = bearer(driver)
    route = client.get("/app/route", headers=h).json()["jobs"]
    assert route[0]["address"] == ADDRESS["texto"] and route[0]["contact"]["phone"] == "1155550000"
    assert route[0]["note"] == "Tercer piso, sin ascensor" and route[0]["items"]
    assert client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "done"}).status_code == 400
    r = client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "on_the_way", "eta_minutes": 20})
    assert r.status_code == 200 and "unos 20 minutos" in _history(client, shop, conv, token)[-1]
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "IN_TRANSIT"
    assert client.post(f"/app/route/{job['id']}/message", headers=h, json={"text": "Estoy en la puerta"}).status_code == 200
    assert _history(client, shop, conv, token)[-1] == "Estoy en la puerta"
    client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "arrived"})
    client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "done"})
    assert "Entregamos e instalamos" in _history(client, shop, conv, token)[-1]
    assert orders.get_order(shop["tenant"], order["id"])["status"] == "DELIVERED"
    assert client.post(f"/app/route/{job['id']}/message", headers=h, json={"text": "hola"}).status_code == 400


def test_failed_delivery_requires_reason_and_can_be_rescheduled(client, accounts, raw_conn, signup):
    shop = _shop(client, accounts, raw_conn, "Reparto Falla")
    driver = _driver(client, shop, signup)
    conv, token, order = _paid_delivery(shop, raw_conn)
    owner = bearer(shop["uid"])
    job = client.post("/app/deliveries", headers=owner, json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "pm", "assigned_to": driver}).json()
    h = bearer(driver)
    assert client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "failed"}).status_code == 400
    client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "failed", "reason": "No había nadie"})
    assert "No había nadie" in _history(client, shop, conv, token)[-1]
    again = client.post("/app/deliveries", headers=owner, json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "day"})
    assert again.status_code == 200


def test_other_driver_and_other_business_cannot_touch_it(client, accounts, raw_conn, signup):
    a = _shop(client, accounts, raw_conn, "Reparto A")
    b = _shop(client, accounts, raw_conn, "Reparto B")
    driver_a, other_a = _driver(client, a, signup), _driver(client, a, signup)
    driver_b = _driver(client, b, signup)
    _, _, order = _paid_delivery(a, raw_conn)
    job = client.post("/app/deliveries", headers=bearer(a["uid"]), json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "am", "assigned_to": driver_a}).json()
    for uid in (other_a, driver_b):
        h = bearer(uid)
        assert client.get("/app/route", headers=h).json()["jobs"] == []
        assert client.post(f"/app/route/{job['id']}/status", headers=h, json={"status": "on_the_way"}).status_code == 404
        assert client.post(f"/app/route/{job['id']}/message", headers=h, json={"text": "x"}).status_code == 404
    # B no puede agendar el pedido de A ni asignarle a alguien de otro negocio.
    assert client.post("/app/deliveries", headers=bearer(b["uid"]), json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "am"}).status_code == 404
    assert client.patch(f"/app/deliveries/{job['id']}", headers=bearer(a["uid"]),
                        json={"assigned_to": driver_b}).status_code == 400


def test_unpaid_or_pickup_orders_cannot_be_scheduled(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Reparto Validación")
    conv, _ = buyer_session.start(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    r = client.post("/app/deliveries", headers=bearer(shop["uid"]), json={
        "order_id": order["id"], "date": reparto.today().isoformat(), "window": "am"})
    assert r.status_code == 400
