"""Panel de resultados: embudo de conversaciones a ventas con datos reales; las conversaciones de
prueba no cuentan; sólo el dueño lo ve; un negocio no ve los números de otro."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import orders
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from app.main import app
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_funnel_sales_and_isolation(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Resultados")
    h = bearer(shop["uid"])
    empty = client.get("/app/insights?days=7", headers=h).json()
    assert empty["funnel"]["conversations"] == 0 and empty["conversion"] is None and len(empty["series"]) == 7

    _say(client, shop, "hola, ¿qué tienen?")                                    # sólo consulta
    _, conv, _ = _say(client, shop, "quiero la canilla de cocina negra")
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    client.post("/app/agent-preview", headers=h, json={"message": "hola"})    # prueba: no cuenta

    r = client.get("/app/insights?days=7", headers=h).json()
    assert r["funnel"] == {"conversations": 2, "with_cart": 1, "with_order": 1, "with_payment": 1}
    assert r["conversion"] == 0.5 and r["solo_agent"] == 2
    assert r["sales"]["orders"] == 1 and r["sales"]["revenue"] == r["sales"]["average_ticket"] > 0
    assert r["top_products"][0]["name"] == "Canilla de cocina negra"
    assert sum(d["conversations"] for d in r["series"]) == 2
    assert sum(d["revenue"] for d in r["series"]) == r["sales"]["revenue"]

    other, _ = accounts("Otra Resultados")
    assert client.get("/app/insights", headers=bearer(other)).json()["funnel"]["conversations"] == 0
    assert client.get("/app/insights", headers={}).status_code == 401
