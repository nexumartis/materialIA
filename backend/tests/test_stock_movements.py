"""Historial de movimientos de stock en el panel: sólo del negocio, con venta, reserva y ajuste."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth, buyer_session
from app.domain import orders
from app.main import app
from app.payments import service
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_movements_show_reserve_sale_and_adjust(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Movimientos")
    owner = bearer(shop["uid"])
    conv, _ = buyer_session.start(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 2)
    order = orders.checkout(shop["tenant"], conv).order
    service.confirm_transfer(shop["tenant"], shop["uid"], order["id"], "BCO-MOV-1", order["total"], "ARS")
    client.patch(f"/app/catalog/{shop['item']}", headers=owner, json={"stock": 20})
    moves = client.get(f"/app/catalog/{shop['item']}/movements", headers=owner).json()
    assert [m["label"] for m in moves][:3] == ["Ajuste de stock", "Venta", "Apartado por pedido"]
    assert moves[1]["order_number"] == order["number"] and moves[1]["on_hand"] == -2
    stranger_uid, _ = accounts("Ajeno Movimientos")
    assert client.get(f"/app/catalog/{shop['item']}/movements", headers=bearer(stranger_uid)).status_code == 404
