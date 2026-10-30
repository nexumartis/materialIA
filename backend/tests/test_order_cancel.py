"""Cancelar un pedido pendiente (cliente desde su chat o dueño desde el panel) libera el stock."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth, buyer_session
from app.domain import orders
from app.main import app
from app.payments import service
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop

HDR = "X-Conversation-Token"


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _pending(shop):
    conv, token = buyer_session.start(shop["tenant"])
    assert orders.add_item(shop["tenant"], conv, shop["item"], 2).status == "ok"
    return conv, token, orders.checkout(shop["tenant"], conv).order


def _reserved(raw_conn, item):
    with raw_conn.cursor() as cur:
        cur.execute("select reserved from stock_levels where item_id = %s", (item,))
        n = cur.fetchone()["reserved"]
    raw_conn.commit()
    return n


def test_buyer_cancels_own_pending_order_and_stock_is_released(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Cancela")
    conv, token, order = _pending(shop)
    other_conv, other_token, _ = _pending(shop)
    url = f"/public/{shop['slug']}/conversations/{conv}/orders/{order['id']}/cancel"
    assert client.post(url).status_code == 404                                    # sin token
    assert client.post(url, headers={HDR: other_token}).status_code == 404        # otro comprador
    assert client.post(f"/public/{shop['slug']}/conversations/{other_conv}/orders/{order['id']}/cancel",
                       headers={HDR: other_token}).status_code == 404             # pedido de otra conversación
    assert _reserved(raw_conn, shop["item"]) == 4
    r = client.post(url, headers={HDR: token})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert _reserved(raw_conn, shop["item"]) == 2
    assert client.post(url, headers={HDR: token}).status_code == 409             # ya no está pendiente


def test_owner_cancels_but_never_a_paid_order(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Dueño Cancela")
    owner = bearer(shop["uid"])
    _, _, order = _pending(shop)
    _, _, paid = _pending(shop)
    service.confirm_transfer(shop["tenant"], shop["uid"], paid["id"], "BCO-CANCEL-1", paid["total"], "ARS")
    assert client.post(f"/app/orders/{paid['id']}/cancel", headers=owner).status_code == 409
    r = client.post(f"/app/orders/{order['id']}/cancel", headers=owner)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    stranger_uid, _ = accounts("Ajeno Cancela")
    assert client.post(f"/app/orders/{paid['id']}/cancel", headers=bearer(stranger_uid)).status_code == 404
