"""Resumen al derivar: con IA lo redacta el modelo sin montos; sin IA, reglas. El carrito sale de la
base. Lo ve la bandeja del negocio y no el de otro."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import handoff, orders
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _derived(client, shop):
    _, conv, token = _say(client, shop, "busco una canilla para cocina, la zona es Quilmes")
    orders.add_item(shop["tenant"], conv, shop["item"], 2)
    _say(client, shop, "quiero hablar con una persona", conv, token)
    return conv


def test_ai_summary_strips_money_and_cart_comes_from_db(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Resumen")
    conv = _derived(client, shop)
    fake = lambda system, user: json.dumps({"quiere": "Una canilla negra por $89.900", "datos": ["Zona Quilmes", "2 unidades"],
                                            "falta": "Confirmar envío a Quilmes y si le hacen precio de 50 mil"})
    handoff.summarize(shop["tenant"], conv, model=fake)
    d = client.get(f"/app/inbox/{conv}", headers=bearer(shop["uid"])).json()["handoff_summary"]
    assert d["by"] == "ia" and "89.900" not in d["quiere"] and "50 mil" not in d["falta"]
    assert d["datos"] == ["Zona Quilmes", "2 unidades"] and d["carrito"] == ["2 × Canilla de cocina negra"]
    other, _ = accounts("Otro Resumen")
    assert client.get(f"/app/inbox/{conv}", headers=bearer(other)).status_code == 404


def test_rules_summary_without_ai(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Resumen 2")
    conv = _derived(client, shop)
    handoff.summarize(shop["tenant"], conv, model=lambda s, u: "esto no es json")
    d = client.get(f"/app/inbox/{conv}", headers=bearer(shop["uid"])).json()["handoff_summary"]
    assert d["by"] == "reglas" and d["falta"] == "Pidió hablar con una persona."
    assert "Quilmes" in d["quiere"]                       # lo que pidió, no «quiero hablar con una persona»


def test_money_forms_are_removed():
    for text in ("Una canilla de USD 120", "u$s 50 cada una", "presupuesto 89900", "100 dólares", "$ 89.900",
                 "le hacen 50 mil", "ARS 3000"):
        assert not any(ch.isdigit() for ch in handoff._clean(text)), text


def test_new_customer_message_refreshes_summary(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Resumen 3")
    conv = _derived(client, shop)
    handoff.summarize(shop["tenant"], conv, model=lambda s, u: "x")
    h = bearer(shop["uid"])
    assert client.get(f"/app/inbox/{conv}", headers=h).json()["handoff_summary"] is not None
    with raw_conn.cursor() as cur:        # el cliente sigue escribiendo
        cur.execute("update conversations set last_customer_message_at = now() + interval '1 second' where id = %s", (conv,))
    raw_conn.commit()
    assert client.get(f"/app/inbox/{conv}", headers=h).json()["handoff_summary"] is None    # queda viejo
    with raw_conn.cursor() as cur:
        cur.execute(f"select 1 from conversations where id = %s and {handoff.STALE_SQL}", (conv,))
        assert cur.fetchone()                                                          # y el worker lo rehace
    raw_conn.commit()
