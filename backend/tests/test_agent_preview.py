"""Vista previa del asistente paso a paso (roadmap etapa 6): el agente responde con el perfil
BORRADOR sin guardarlo, en una conversación de prueba sin pedidos, stock ni CRM que se borra al
reiniciar (o la limpia el worker). Plantilla de rubro sin aplicarla y 409 estructurado."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import evals
from app.main import app
from app.schemas import MAX_PREVIEW_MESSAGES
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def shop(client, accounts, raw_conn):
    return _shop(client, accounts, raw_conn, "Tienda Asistente")


def _counts(raw_conn, tenant):
    with raw_conn.cursor() as cur:
        cur.execute("select (select count(*) from conversations where tenant_id = %(t)s) c, "
                    "(select count(*) from orders where tenant_id = %(t)s and status <> 'CART_OPEN') o, "
                    "(select count(*) from orders where tenant_id = %(t)s) all_o, "
                    "(select count(*) from opportunities where tenant_id = %(t)s) p, "
                    "(select coalesce(sum(reserved), 0) from stock_levels where tenant_id = %(t)s) r", {"t": tenant})
        row = dict(cur.fetchone())
    raw_conn.commit()
    return row


def _say(client, owner, message, conv=None, profile=None):
    r = client.post("/app/agent-preview", headers=owner,
                    json={"message": message, "conversation_id": conv, "profile": profile})
    assert r.status_code == 200, r.text
    return r.json()


def test_preview_uses_the_draft_one_message_at_a_time_and_leaves_nothing(client, shop, raw_conn):
    owner = bearer(shop["uid"])
    before_profile = client.get("/app/agent-profile", headers=owner).json()
    before = _counts(raw_conn, shop["tenant"])
    draft = {"greeting": "Hola, soy Ramona de prueba", "shipping": "Envíos a Rosario por $3.000"}
    first = _say(client, owner, "hola", profile=draft)
    conv = first["conversation_id"]
    assert first["reply"] == "Hola, soy Ramona de prueba" and first["mode"] == "mock"
    assert "Rosario" in _say(client, owner, "¿hacen envíos?", conv, draft)["reply"]
    for m in ("canilla de cocina negra", "agregame la 1", "quiero hablar con una persona"):
        _say(client, owner, m, conv, draft)
    mid = _counts(raw_conn, shop["tenant"])
    # Sin pedido confirmado, CRM ni reserva (el carrito de prueba es transitorio y se borra al reiniciar).
    assert mid["o"] == before["o"] and mid["p"] == before["p"] and mid["r"] == before["r"]
    assert conv not in [c["id"] for c in client.get("/app/inbox?filter=todas", headers=owner).json()]
    assert client.delete(f"/app/agent-preview/{conv}", headers=owner).json() == {"deleted": True}
    assert _counts(raw_conn, shop["tenant"]) == before
    after = client.get("/app/agent-profile", headers=owner).json()
    assert after["greeting"] == before_profile["greeting"] and after["version"] == before_profile["version"]


def test_preview_is_isolated_and_capped(client, shop, accounts, raw_conn):
    owner = bearer(shop["uid"])
    conv = _say(client, owner, "hola")["conversation_id"]
    other = _shop(client, accounts, raw_conn, "Otra Tienda Asistente")
    stranger = bearer(other["uid"])
    assert client.post("/app/agent-preview", headers=stranger,
                       json={"message": "hola", "conversation_id": conv}).status_code == 404
    assert client.delete(f"/app/agent-preview/{conv}", headers=stranger).json() == {"deleted": False}
    public_conv = client.post(f"/public/{shop['slug']}/chat", json={"message": "hola"}).json()["conversation_id"]
    assert client.post("/app/agent-preview", headers=owner,
                       json={"message": "hola", "conversation_id": public_conv}).status_code == 404   # sólo canal eval
    for _ in range(MAX_PREVIEW_MESSAGES - 1):
        _say(client, owner, "hola", conv)
    capped = client.post("/app/agent-preview", headers=owner, json={"message": "hola", "conversation_id": conv})
    assert capped.status_code == 409 and "reiniciala" in capped.json()["detail"]
    assert client.post("/app/agent-preview", json={"message": "hola"}).status_code == 401
    assert client.post("/app/agent-preview", headers=owner, json={"message": "   "}).status_code == 400
    assert client.post("/app/agent-preview", headers=owner,
                       json={"message": "hola", "profile": {"tone": "grosero"}}).status_code == 400


def test_failed_first_turn_and_abandoned_previews_are_cleaned(client, shop, raw_conn, monkeypatch):
    from app.agent import sales_agent
    owner = bearer(shop["uid"])
    before = _counts(raw_conn, shop["tenant"])

    def boom(*_, **__):
        raise RuntimeError("LLM caído")
    with monkeypatch.context() as m:
        m.setattr(sales_agent, "_rules_reply", boom)
        with pytest.raises(RuntimeError):
            client.post("/app/agent-preview", headers=owner, json={"message": "busco una canilla"})
    assert _counts(raw_conn, shop["tenant"]) == before      # la que no llegó a empezar ya se borró
    _say(client, owner, "hola")                              # otra vista previa abandonada
    with raw_conn.cursor() as cur:                           # pasó el tiempo
        cur.execute("update conversations set created_at = now() - interval '2 hours' "
                    "where tenant_id = %s and channel = 'eval'", (shop["tenant"],))
    raw_conn.commit()
    assert evals.cleanup_stale() >= 1
    assert _counts(raw_conn, shop["tenant"]) == before


def test_template_is_returned_without_applying_it(client, shop):
    owner = bearer(shop["uid"])
    before = client.get("/app/agent-profile", headers=owner).json()
    t = client.get("/app/agent-templates/sanitarios", headers=owner).json()
    assert t["business_type"] == "sanitarios" and t["greeting"] and t["faq"]
    assert not {"shipping", "hours", "payment_methods"} & set(t)
    after = client.get("/app/agent-profile", headers=owner).json()
    assert after["version"] == before["version"] and after["greeting"] == before["greeting"]
    assert client.get("/app/agent-templates/inexistente", headers=owner).status_code == 404


def test_failing_evals_409_carries_a_structured_code(client, shop):
    owner = bearer(shop["uid"])
    client.post("/app/agent-evals", headers=owner,
                json={"message": "hola", "expect_contains": ["palabra-imposible"], "expect_not_contains": []})
    r = client.put("/app/agent-profile", headers=owner, json={"greeting": "Hola", "require_evals": True})
    assert r.status_code == 409 and r.headers["x-error-code"] == "evals_failed"
