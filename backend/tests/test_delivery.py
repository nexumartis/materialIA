"""Entrega antes de confirmar: envío (dirección normalizada, zona y costo del negocio, contacto) o
retiro en el local. Sin opciones cargadas no pregunta nada. El costo de envío suma al total y nunca
se inventa."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import delivery, orders
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop

ADDR = {"Av Mitre 1234": {"calle": "AV BARTOLOME MITRE", "altura": 1234, "localidad": "Avellaneda",
                          "departamento": "Avellaneda", "provincia": "Buenos Aires",
                          "texto": "AV BARTOLOME MITRE 1234, Avellaneda, Buenos Aires"},
        "San Martin 500": {"calle": "SAN MARTIN", "altura": 500, "localidad": "Mendoza", "departamento": "Capital",
                           "provincia": "Mendoza", "texto": "SAN MARTIN 500, Mendoza, Mendoza"}}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(delivery, "_georef_address",
                        lambda street, place: next((v for k, v in ADDR.items() if k.lower() in street.lower()), None))


def _setup(client, accounts, raw_conn, name, policies):
    shop = _shop(client, accounts, raw_conn, name)
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = policies
    assert client.put("/app/agent-profile", headers=h, json=profile).status_code == 200
    _, conv, tok = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    return shop, conv, tok


def test_delivery_to_covered_zone_adds_cost(accounts, raw_conn):
    client = TestClient(app)
    shop, conv, tok = _setup(client, accounts, raw_conn, "Tienda Entrega",
                             {"delivery_zones": "Zona Sur: 4000, CABA", "pickup_address": "Av. Belgrano 100, CABA"})
    j, _, _ = _say(client, shop, "la compro", conv, tok)
    assert "¿cómo lo querés recibir?" in j["reply"] and "Retiro en el local: Av. Belgrano 100" in j["reply"]
    j, _, _ = _say(client, shop, "envio a domicilio", conv, tok)
    assert "calle, número y localidad" in j["reply"]
    j, _, _ = _say(client, shop, "Av Mitre 1234, Avellaneda", conv, tok)
    assert "AV BARTOLOME MITRE 1234" in j["reply"] and "Zona Sur cuesta $4.000" in j["reply"]
    j, _, _ = _say(client, shop, "Ana Gomez 11 5555 4444", conv, tok)
    assert "Envío: $4.000" in j["reply"] and "Entrega: Envío a AV BARTOLOME MITRE 1234" in j["reply"]
    cart = orders.get_cart(shop["tenant"], conv)
    assert cart["shipping"] == 4000 and cart["total"] == cart["subtotal"] + 4000
    assert cart["delivery_contact"] == {"name": "Ana Gomez", "phone": "1155554444"}
    j, _, _ = _say(client, shop, "si", conv, tok)
    assert "Pedido #" in j["reply"]


def test_out_of_zone_offers_pickup_and_pickup_has_no_cost(accounts, raw_conn):
    client = TestClient(app)
    shop, conv, tok = _setup(client, accounts, raw_conn, "Tienda Entrega 2",
                             {"delivery_zones": "CABA: 5000", "pickup_address": "Av. Belgrano 100, CABA"})
    _say(client, shop, "la compro", conv, tok)
    _say(client, shop, "1", conv, tok)
    j, _, _ = _say(client, shop, "San Martin 500, Mendoza", conv, tok)
    assert "no hacemos envíos" in j["reply"] and "¿Lo retirás en el local?" in j["reply"]
    j, _, _ = _say(client, shop, "si", conv, tok)
    assert "Entrega: Retiro en el local" in j["reply"] and "Envío:" not in j["reply"]
    assert orders.get_cart(shop["tenant"], conv)["shipping"] == 0


def test_unknown_address_twice_goes_to_a_person_and_no_options_no_question(accounts, raw_conn):
    client = TestClient(app)
    shop, conv, tok = _setup(client, accounts, raw_conn, "Tienda Entrega 3", {"delivery_zones": "CABA: 5000"})
    j, _, _ = _say(client, shop, "la compro", conv, tok)
    assert "Envío a domicilio" in j["reply"]
    _say(client, shop, "si", conv, tok)
    j, _, _ = _say(client, shop, "por ahi cerca 123", conv, tok)
    assert "No encontré esa dirección" in j["reply"]
    j, _, _ = _say(client, shop, "calle falsa 999", conv, tok)
    assert "una persona del equipo" in j["reply"] and j["requires_human"]
    shop2, conv2, tok2 = _setup(client, accounts, raw_conn, "Tienda Sin Entrega", {})
    j, _, _ = _say(client, shop2, "la compro", conv2, tok2)
    assert "¿Confirmás?" in j["reply"] and "recibir" not in j["reply"]


def test_review_cases_ship_wins_change_to_pickup_names_and_redaction(accounts, raw_conn):
    client = TestClient(app)
    pol = {"delivery_zones": "Zona Sur: 4000", "pickup_address": "Av. Belgrano 100, CABA", "min_order_total": 999999}
    shop, conv, tok = _setup(client, accounts, raw_conn, "Tienda Entrega 4", {**pol, "min_order_total": None})
    _say(client, shop, "la compro", conv, tok)
    j, _, _ = _say(client, shop, "envio a domicilio, te paso la direccion", conv, tok)
    assert "calle, número y localidad" in j["reply"]                       # «paso» no lo vuelve retiro
    j, _, _ = _say(client, shop, "no, mejor lo retiro", conv, tok)
    assert "Entrega: Retiro en el local" in j["reply"]                     # cambia a retiro, no «dirección inválida»

    shop, conv, tok = _setup(client, accounts, raw_conn, "Tienda Entrega 5", {**pol, "min_order_total": None})
    _say(client, shop, "la compro", conv, tok)
    _say(client, shop, "1", conv, tok)
    _say(client, shop, "Av Mitre 1234, zona sur", conv, tok)
    j, _, _ = _say(client, shop, "José Ñúñez 11 5555 4444", conv, tok)
    assert j["reply"].index("Envío: $4.000") < j["reply"].index("Total:")   # el envío antes del total
    assert orders.get_cart(shop["tenant"], conv)["delivery_contact"]["name"] == "José Ñúñez"
    client.post(f"/app/inbox/{conv}/redact", headers=bearer(shop["uid"]))
    cart = orders.get_cart(shop["tenant"], conv)
    assert cart["delivery_contact"]["phone"] == "[oculto]" and "MITRE" not in str(cart["delivery_address"])
