"""Centro de avisos: junta derivaciones sin atender, pedidos a revisar, comprobantes por cotejar,
turnos nuevos y calificaciones bajas; sólo del propio negocio."""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import booking, orders
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_alerts_collects_and_isolates(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Avisos")
    h = bearer(shop["uid"])
    assert client.get("/app/alerts", headers=h).json() == []
    _, conv, _ = _say(client, shop, "quiero hablar con una persona")
    order = None
    _, c2, _ = _say(client, shop, "hola")
    orders.add_item(shop["tenant"], c2, shop["item"], 1)
    order = orders.checkout(shop["tenant"], c2).order
    with raw_conn.cursor() as cur:
        cur.execute("update orders set attention_reason = 'amount_mismatch' where id = %s", (order["id"],))
    raw_conn.commit()
    cfg = booking.validate({"services": "Retiro: 30", "hours": "lun-dom 0-23"})
    with orders.tenant_tx(shop["tenant"]) as cur:
        start = booking.free_slots(cur, shop["tenant"], cfg, cfg["services"][0])[0]
        booking.book(cur, shop["tenant"], conv, cfg, cfg["services"][0], start)
    kinds = {a["kind"]: a for a in client.get("/app/alerts", headers=h).json()}
    assert set(kinds) == {"handoff", "order", "appointment"}
    assert kinds["handoff"]["href"] == f"#/conversaciones/{conv}"
    assert "el monto pagado no coincide" in kinds["order"]["text"]
    # Tomar la conversación saca el aviso de derivación.
    client.post(f"/app/inbox/{conv}/take", headers=h)
    assert "handoff" not in {a["kind"] for a in client.get("/app/alerts", headers=h).json()}
    other, _ = accounts("Otra Avisos")
    assert client.get("/app/alerts", headers=bearer(other)).json() == []
