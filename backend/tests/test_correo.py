"""Envío por correo y módulos del negocio: una zona «por correo» no ofrece franjas y avisa la demora;
«Todo el país» cubre lo que no cae en otra zona; al despachar se carga correo + seguimiento, el cliente
lo recibe y el agente lo informa; los módulos ordenan el panel y sólo los cambia el dueño."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import delivery, orders
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop

CORDOBA = {"calle": "SAN MARTIN", "altura": 500, "localidad": "Córdoba", "departamento": "Capital",
           "provincia": "Córdoba", "texto": "SAN MARTIN 500, Córdoba", "lat": -31.41, "lon": -64.18}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(delivery, "_georef_address", lambda street, place: CORDOBA if "martin" in street.lower() else None)


@pytest.fixture
def client():
    return TestClient(app)


def _setup(client, accounts, raw_conn, name):
    shop = _shop(client, accounts, raw_conn, name)
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"delivery_zones": "CABA: 5000, Todo el país: 9000", "courier_zones": ["Todo el país"],
                           "courier_eta": "3 a 5 días hábiles"}
    assert client.put("/app/agent-profile", headers=h, json=profile).status_code == 200
    client.put("/app/deliveries/slots", headers=h, json={"enabled": True, "days": [0, 1, 2, 3, 4, 5, 6],
                                                        "windows": ["am"], "capacity": 5, "horizon_days": 3, "lead_days": 1})
    return shop


def _buy(client, shop):
    _, conv, tok = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    _say(client, shop, "la compro", conv, tok)
    _say(client, shop, "si", conv, tok)
    j, _, _ = _say(client, shop, "San Martin 500, Cordoba", conv, tok)
    return conv, tok, j


def test_courier_zone_skips_slots_and_tells_eta(client, accounts, raw_conn):
    shop = _setup(client, accounts, raw_conn, "Correo Chat")
    conv, tok, j = _buy(client, shop)
    assert "Todo el país cuesta $9.000" in j["reply"] and "por correo (3 a 5 días hábiles)" in j["reply"]
    j, _, _ = _say(client, shop, "Ana 11 5555 4444", conv, tok)
    assert "¿Confirmás?" in j["reply"] and "¿Cuándo te queda" not in j["reply"]


def test_ship_notifies_customer_and_agent_reports_tracking(client, accounts, raw_conn):
    shop = _setup(client, accounts, raw_conn, "Correo Despacho")
    conv, tok, _ = _buy(client, shop)
    _say(client, shop, "Ana 11 5555 4444", conv, tok)
    _say(client, shop, "si", conv, tok)
    order = orders.conversation_orders(shop["tenant"], conv)[0]
    h = bearer(shop["uid"])
    assert client.post(f"/app/orders/{order['id']}/shipment", headers=h,
                       json={"carrier": "andreani", "tracking_code": "360002"}).status_code == 400     # impago
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    service.receive_notification("simulated", headers, {}, body)
    for bad in ({"carrier": "dhl", "tracking_code": "360002"}, {"carrier": "andreani", "tracking_code": "<x>"},
                {"carrier": "otro", "tracking_code": "ABC123"}):
        assert client.post(f"/app/orders/{order['id']}/shipment", headers=h, json=bad).status_code == 400, bad
    r = client.post(f"/app/orders/{order['id']}/shipment", headers=h,
                    json={"carrier": "andreani", "tracking_code": "360 0021 4567"})
    assert r.status_code == 200 and r.json()["status"] == "DISPATCHED" and r.json()["tracking_code"] == "36000214567"
    hist = client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={"X-Conversation-Token": tok}).json()
    assert "salió por Andreani" in hist["messages"][-1]["content"] and "36000214567" in hist["messages"][-1]["content"]
    j, _, _ = _say(client, shop, "como va mi pedido?", conv, tok)
    assert "Andreani" in j["reply"] and "36000214567" in j["reply"]


def test_modules_owner_only_and_in_me(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Correo Módulos")
    h = bearer(shop["uid"])
    assert all(client.get("/app/me", headers=h).json()["modules"].values())        # existentes: todo prendido
    r = client.put("/app/modules", headers=h, json={"reparto": False, "turnos": False})
    assert r.status_code == 200 and r.json()["modules"]["reparto"] is False and r.json()["modules"]["correo"] is True
    assert client.get("/app/me", headers=h).json()["modules"]["turnos"] is False
    assert client.put("/app/modules", headers=h, json={"magia": True}).status_code == 400
    assert {m["key"] for m in client.get("/app/modules", headers=h).json()["catalog"]} >= {"turnos", "reparto", "correo"}


def test_courier_zone_must_exist(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Correo Validación")
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"delivery_zones": "CABA: 5000", "courier_zones": ["Interior"]}
    assert client.put("/app/agent-profile", headers=h, json=profile).status_code == 400
