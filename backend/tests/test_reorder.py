"""Recompra: «repetí mi pedido» arma el carrito con el último pedido PAGADO del cliente recordado,
con el precio y el stock de HOY; lo que no se puede vender se avisa. Sin cliente recordado o sin
pedidos, no inventa nada."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import orders
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer

HDR = "X-Conversation-Token"
KEY_H = {"X-Buyer-Key": "r" * 32}
CSV = """sku;nombre;categoria;precio;stock
REM-1;Remera básica;remeras;15000;10
GOR-1;Gorra lisa;accesorios;8000;1
"""


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _chat(client, slug, text, conv=None, token=None):
    h = {**KEY_H, **({HDR: token} if token else {})}
    j = client.post(f"/public/{slug}/chat", json={"message": text, "conversation_id": conv}, headers=h).json()
    return j, j["conversation_id"], token or j.get("conversation_token")


def test_reorder_uses_todays_price_and_stock(accounts):
    client = TestClient(app)
    uid, tenant = accounts("Ropa Recompra")
    client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    slug = client.get("/app/agent-profile", headers=bearer(uid)).json()["public_slug"]
    with orders.tenant_tx(tenant) as cur:
        cur.execute("select id, sku from catalog_items where tenant_id = %s", (tenant,))
        ids = {r["sku"]: str(r["id"]) for r in cur.fetchall()}
    # Primera compra (pagada): 2 remeras y 1 gorra.
    _, conv, tok = _chat(client, slug, "hola")
    orders.add_item(tenant, conv, ids["REM-1"], 2)
    orders.add_item(tenant, conv, ids["GOR-1"], 1)
    order = orders.checkout(tenant, conv).order
    pref = service.start_payment(tenant, order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    # Cambia el precio de la remera; la gorra se agotó (era la última).
    client.post("/app/catalog/import", headers=bearer(uid),
                json={"csv": "sku;nombre;categoria;precio;stock\nREM-1;Remera básica;remeras;17000;10\n"})
    j, conv2, tok2 = _chat(client, slug, "hola de nuevo")
    j, _, _ = _chat(client, slug, "quiero lo mismo que la otra vez", conv2, tok2)
    items = {i["name"]: (i["qty"], i["unit_price"]) for i in j["cart"]["items"]}
    assert items == {"Remera básica": (2, 17000)}                          # precio de hoy
    assert "Gorra lisa (sin stock)" in j["reply"]


def test_no_customer_or_no_orders_invents_nothing(accounts):
    client = TestClient(app)
    uid, tenant = accounts("Ropa Recompra 2")
    client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    slug = client.get("/app/agent-profile", headers=bearer(uid)).json()["public_slug"]
    j, conv, tok = _chat(client, slug, "repetime el pedido")
    assert not (j.get("cart") or {}).get("items") and "Te armé el carrito" not in j["reply"]
