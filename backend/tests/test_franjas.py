"""Franjas en el chat: con el reparto configurado, después de la dirección el agente ofrece día y franja
con cupo (primero donde ya hay una entrega cerca); la elección queda en el pedido, ocupa cupo mientras
espera el pago y, al pagarse, la entrega se agenda sola. Una franja llena nunca se ofrece."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import delivery, orders, reparto
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop

HOME = {"calle": "AV BARTOLOME MITRE", "altura": 1234, "localidad": "Avellaneda", "departamento": "Avellaneda",
        "provincia": "Buenos Aires", "texto": "AV BARTOLOME MITRE 1234, Avellaneda", "lat": -34.6625, "lon": -58.3650}
NEAR = {**HOME, "texto": "AV MITRE 1800, Avellaneda", "lat": -34.6660, "lon": -58.3700}       # ~0,6 km
FAR = {**HOME, "texto": "SAN MARTIN 500, Pilar", "lat": -34.4587, "lon": -58.9142}           # ~55 km


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(delivery, "_georef_address", lambda street, place: HOME if "mitre" in street.lower() else None)


@pytest.fixture
def client():
    return TestClient(app)


def _setup(client, accounts, raw_conn, name, capacity=3):
    shop = _shop(client, accounts, raw_conn, name)
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"delivery_zones": "Zona Sur: 4000"}
    assert client.put("/app/agent-profile", headers=h, json=profile).status_code == 200
    cfg = {"enabled": True, "days": [0, 1, 2, 3, 4, 5, 6], "windows": ["am", "pm"], "capacity": capacity,
           "horizon_days": 4, "lead_days": 1}
    assert client.put("/app/deliveries/slots", headers=h, json=cfg).status_code == 200
    return shop


def _job(raw_conn, shop, day, window, address):
    """Una entrega ya agendada (pedido pagado con esa dirección)."""
    with raw_conn.cursor() as cur:
        cur.execute("insert into orders (tenant_id, status, total, delivery_method, delivery_address, paid_at) "
                    "values (%s, 'PAID', 1000, 'delivery', %s::jsonb, now()) returning id", (shop["tenant"], json.dumps(address)))
        oid = cur.fetchone()["id"]
        cur.execute("insert into delivery_jobs (tenant_id, order_id, scheduled_date, time_window) values (%s, %s, %s, %s)",
                    (shop["tenant"], oid, day, window))
    raw_conn.commit()


def test_suggest_prefers_nearby_and_skips_full(client, accounts, raw_conn):
    shop = _setup(client, accounts, raw_conn, "Franjas Ranking", capacity=2)
    first = reparto.today() + timedelta(days=1)
    _job(raw_conn, shop, first, "am", FAR)
    _job(raw_conn, shop, first, "am", FAR)                       # mañana a la mañana: lleno
    _job(raw_conn, shop, first + timedelta(days=2), "pm", NEAR)  # en 3 días a la tarde: entrega a 600 m
    from app.db import tenant_tx
    with tenant_tx(shop["tenant"]) as cur:
        opts = reparto.suggest(cur, shop["tenant"], HOME)
    assert (opts[0]["date"], opts[0]["window"]) == ((first + timedelta(days=2)).isoformat(), "pm")
    assert opts[0]["near_km"] is not None and opts[0]["near_km"] < 1
    assert (opts[1]["date"], opts[1]["window"]) == (first.isoformat(), "pm")     # la más temprana con lugar
    assert opts[1]["near_km"] is None
    assert all(not (o["date"] == first.isoformat() and o["window"] == "am") for o in opts)


def test_chat_offers_slots_and_paid_order_schedules_itself(client, accounts, raw_conn):
    shop = _setup(client, accounts, raw_conn, "Franjas Chat")
    _, conv, tok = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    _say(client, shop, "la compro", conv, tok)
    _say(client, shop, "si", conv, tok)                 # sólo hay envío: «¿te sirve así?»
    _say(client, shop, "Av Mitre 1234, Avellaneda", conv, tok)
    j, _, _ = _say(client, shop, "Ana Gomez 11 5555 4444", conv, tok)
    assert "¿Cuándo te queda mejor recibirlo?" in j["reply"] and "1. " in j["reply"]
    j, _, _ = _say(client, shop, "la 2", conv, tok)
    cart = orders.get_cart(shop["tenant"], conv)
    assert cart["delivery_date"] and cart["delivery_window"]
    assert reparto.describe_slot(cart) in j["reply"] and "¿Confirmás?" in j["reply"]
    j, _, _ = _say(client, shop, "si", conv, tok)
    order = next(o for o in orders.conversation_orders(shop["tenant"], conv) if o["status"] == "PENDING_PAYMENT")
    # Mientras espera el pago, ocupa cupo.
    day = date_of(order)
    assert client.get(f"/app/deliveries?date={day}", headers=bearer(shop["uid"])).json()["load"][order["delivery_window"]] == 1
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    board = client.get(f"/app/deliveries?date={day}", headers=bearer(shop["uid"])).json()
    assert [(x["order_id"], x["source"]) for x in board["jobs"]] == [(order["id"], "chat")]
    hist = client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={"X-Conversation-Token": tok}).json()
    assert any("queda agendado" in m["content"] for m in hist["messages"][-2:])


def test_other_day_goes_to_checkout_without_slot(client, accounts, raw_conn):
    shop = _setup(client, accounts, raw_conn, "Franjas Otro Día")
    _, conv, tok = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    _say(client, shop, "la compro", conv, tok)
    _say(client, shop, "si", conv, tok)                 # sólo hay envío: «¿te sirve así?»
    _say(client, shop, "Av Mitre 1234, Avellaneda", conv, tok)
    _say(client, shop, "Ana 11 5555 4444", conv, tok)
    j, _, _ = _say(client, shop, "ninguno, otro dia", conv, tok)
    assert "¿Confirmás?" in j["reply"] and orders.get_cart(shop["tenant"], conv)["delivery_date"] is None


def test_slots_off_keeps_old_flow(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Franjas Apagadas")
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"delivery_zones": "Zona Sur: 4000"}
    client.put("/app/agent-profile", headers=h, json=profile)
    _, conv, tok = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    _say(client, shop, "la compro", conv, tok)
    _say(client, shop, "si", conv, tok)                 # sólo hay envío: «¿te sirve así?»
    _say(client, shop, "Av Mitre 1234, Avellaneda", conv, tok)
    j, _, _ = _say(client, shop, "Ana 11 5555 4444", conv, tok)
    assert "¿Confirmás?" in j["reply"] and "¿Cuándo te queda" not in j["reply"]
    assert client.put("/app/deliveries/slots", headers=h, json={"days": [], "windows": ["am"]}).status_code == 400


def date_of(order):
    return order["delivery_date"]


def test_route_is_ordered_by_proximity(client, accounts, raw_conn):
    shop = _setup(client, accounts, raw_conn, "Franjas Ruta")
    day = reparto.today()
    for addr in (HOME, FAR, NEAR):               # se cargan en este orden (números de pedido crecientes)
        _job(raw_conn, shop, day, "am", addr)
    with raw_conn.cursor() as cur:
        cur.execute("update delivery_jobs set assigned_to = %s where tenant_id = %s", (shop["uid"], shop["tenant"]))
    raw_conn.commit()
    route = client.get("/app/route", headers=bearer(shop["uid"])).json()["jobs"]
    assert [r["address"] for r in route] == [HOME["texto"], NEAR["texto"], FAR["texto"]]
