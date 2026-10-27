"""Cada negocio arma su agente: perfil con plantilla por rubro, catálogo por CSV y edición,
pedidos en el panel y link público de tienda. Todo con el negocio de la sesión (RLS)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, bearer

CSV = """sku;nombre;categoria;marca;precio;stock;descripcion;foto_url;color;ambiente;a_pedido
CAN-1;Canilla de cocina negra;griferia;Marca X;89.900;5;Pico alto;https://ejemplo.test/c1.jpg;negro;cocina;
CAN-2;Canilla de baño cromo;griferia;Marca X;45.000,50;0;;;cromo;baño;
INO-1;Inodoro a pedido;sanitarios;Marca Y;;;Se encarga;;blanco;baño;si
MAL-1;Producto sin precio;griferia;;;3;;;;;
MAL-2;Foto rara;griferia;;1000;1;;ftp://x;;;
"""


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


def test_profile_starts_generic_and_template_preloads_by_business_type(client, accounts):
    uid, _ = accounts("Sanitarios Pérez")
    p = client.get("/app/agent-profile", headers=bearer(uid)).json()
    assert p["business_type"] == "generico" and p["public_slug"].startswith("sanitarios-perez-")
    p = client.put("/app/agent-profile", headers=bearer(uid),
                   json={"business_type": "sanitarios", "apply_template": True}).json()
    assert p["business_type"] == "sanitarios" and p["seller_name"] == "Caro"
    assert "Sanitarios Pérez" in p["greeting"] and p["faq"]
    p = client.put("/app/agent-profile", headers=bearer(uid),
                   json={"seller_name": "Mari", "tone": "formal", "public_slug": "Sanitarios Pérez Oficial",
                         "faq": [{"q": "¿Hacen envíos?", "a": "Sí, a todo Rosario."}, {"q": "", "a": "x"}],
                         "shipping": "Rosario y alrededores"}).json()
    assert p["seller_name"] == "Mari" and p["tone"] == "formal"
    assert p["public_slug"] == "sanitarios-perez-oficial" and len(p["faq"]) == 1


def test_profile_validation_and_unique_slug(client, accounts):
    uid_a, _ = accounts("Negocio A")
    uid_b, _ = accounts("Negocio B")
    client.put("/app/agent-profile", headers=bearer(uid_a), json={"public_slug": "mi-tienda-unica"})
    r = client.put("/app/agent-profile", headers=bearer(uid_b), json={"public_slug": "mi-tienda-unica"})
    assert r.status_code == 409
    assert client.put("/app/agent-profile", headers=bearer(uid_b), json={"tone": "agresivo"}).status_code == 400
    assert client.put("/app/agent-profile", headers=bearer(uid_b), json={"seller_name": " "}).status_code == 400


def test_csv_import_creates_validates_and_updates(client, accounts):
    uid, _ = accounts("Importadora")
    r = client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV}).json()
    assert r["created"] == 3 and r["updated"] == 0
    assert {e["sku"] for e in r["errors"]} == {"MAL-1", "MAL-2"}
    assert all(e["fila"] in (5, 6) for e in r["errors"])
    items = {i["sku"]: i for i in client.get("/app/catalog", headers=bearer(uid)).json()}
    assert items["CAN-1"]["price"] == 89900 and items["CAN-1"]["available"] == 5
    assert items["CAN-2"]["price"] == 45000.5 and items["CAN-2"]["available"] == 0
    assert items["INO-1"]["pricing_mode"] == "custom_quote"
    assert items["CAN-1"]["specs"] == {"color": "negro", "ambiente": "cocina"}
    # Reimportar actualiza (no duplica) y cambia precio/stock.
    again = "sku,nombre,precio,stock\nCAN-1,Canilla de cocina negra,95000,8\n"
    r = client.post("/app/catalog/import", headers=bearer(uid), json={"csv": again}).json()
    assert r == {"created": 0, "updated": 1, "errors": []}
    items = {i["sku"]: i for i in client.get("/app/catalog", headers=bearer(uid)).json()}
    assert items["CAN-1"]["price"] == 95000 and items["CAN-1"]["on_hand"] == 8
    assert client.post("/app/catalog/import", headers=bearer(uid),
                       json={"csv": "codigo,titulo\nx,y\n"}).status_code == 400


def test_edit_product_price_stock_and_active(client, accounts):
    uid, _ = accounts("Editora")
    client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    item = next(i for i in client.get("/app/catalog", headers=bearer(uid)).json() if i["sku"] == "CAN-1")
    r = client.patch(f"/app/catalog/{item['id']}", headers=bearer(uid), json={"price": 70000, "stock": 2}).json()
    assert r["price"] == 70000 and r["on_hand"] == 2
    r = client.patch(f"/app/catalog/{item['id']}", headers=bearer(uid), json={"active": False}).json()
    assert r["active"] is False
    assert client.patch(f"/app/catalog/{item['id']}", headers=bearer(uid), json={"stock": -1}).status_code == 400


def test_other_business_cannot_edit_my_products(client, accounts):
    uid_a, _ = accounts("Dueña A")
    uid_b, _ = accounts("Dueño B")
    client.post("/app/catalog/import", headers=bearer(uid_a), json={"csv": CSV})
    item = client.get("/app/catalog", headers=bearer(uid_a)).json()[0]
    assert client.get("/app/catalog", headers=bearer(uid_b)).json() == []
    assert client.patch(f"/app/catalog/{item['id']}", headers=bearer(uid_b), json={"price": 1}).status_code == 404


def test_public_store_sells_with_the_business_profile_and_catalog(client, accounts):
    uid, _ = accounts("Grifería Online")
    client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    profile = client.put("/app/agent-profile", headers=bearer(uid), json={
        "business_type": "sanitarios", "apply_template": True}).json()
    client.put("/app/agent-profile", headers=bearer(uid), json={
        "faq": [{"q": "¿Hacen envíos?", "a": "Sí, enviamos a todo Rosario por $5.000."}]})
    slug = profile["public_slug"]

    store = client.get(f"/public/{slug}").json()
    assert store["name"] == "Grifería Online" and store["seller_name"] == "Caro"
    r = client.post(f"/public/{slug}/chat", json={"message": "tenés canilla negra de cocina?"}).json()
    assert "$89.900" in r["reply"] and r["ui"]["products"][0]["image_url"] == "https://ejemplo.test/c1.jpg"
    buyer = {"X-Conversation-Token": r["conversation_token"]}
    r = client.post(f"/public/{slug}/chat", headers=buyer, json={"message": "hacen envíos?",
                                                                  "conversation_id": r["conversation_id"]}).json()
    assert "todo Rosario por $5.000" in r["reply"]
    r = client.post(f"/public/{slug}/chat", headers=buyer, json={"message": "dan factura?",
                                                                  "conversation_id": r["conversation_id"]}).json()
    assert "persona" in r["reply"] and r["requires_human"] is True
    assert client.get("/public/no-existe-esta").status_code == 404


def test_panel_orders_and_fulfillment(client, accounts):
    uid, _ = accounts("Vendedora")
    client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    slug = client.get("/app/agent-profile", headers=bearer(uid)).json()["public_slug"]
    conv, buyer = None, {}
    for m in ("canilla negra de cocina", "agregame la 1", "comprar", "sí"):
        r = client.post(f"/public/{slug}/chat", headers=buyer, json={"message": m, "conversation_id": conv}).json()
        conv = r["conversation_id"]
        buyer = buyer or {"X-Conversation-Token": r["conversation_token"]}
    orders_ = client.get("/app/orders", headers=bearer(uid)).json()
    assert len(orders_) == 1 and orders_[0]["status"] == "PENDING_PAYMENT"
    oid = orders_[0]["id"]
    assert client.post(f"/app/orders/{oid}/status?status=DISPATCHED", headers=bearer(uid)).status_code == 400
