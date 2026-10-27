"""Versiones del perfil, políticas que hace cumplir el código y herramientas por negocio."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.agent.sales_agent import handle_sales_message
from app.db import tenant_tx
from app.domain import agent_profile, orders
from app.main import app
from jwt_helpers import KEY, bearer

from conftest import new_conversation


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _profile(shop, **changes):
    """Crea/actualiza el perfil del negocio de prueba como lo haría el panel."""
    with tenant_tx(shop["tenant"]) as cur:
        agent_profile._ensure(cur, shop["tenant"], "Sanitarios Test")
        return agent_profile._update(cur, shop["tenant"], agent_profile.validate(changes))


class Chat:
    def __init__(self, tenant):
        self.tenant, self.conv, self.last = tenant, None, None

    def say(self, text):
        self.last = handle_sales_message(self.tenant, text, self.conv)
        self.conv = self.last.conversation_id
        return self.last.reply


# --- Versiones ------------------------------------------------------------------------
def test_versions_and_restore_via_panel(accounts):
    client = TestClient(app)
    uid, _ = accounts("Versionada")
    v1 = client.get("/app/agent-profile", headers=bearer(uid)).json()
    assert v1["version"] == 1
    v2 = client.put("/app/agent-profile", headers=bearer(uid), json={"seller_name": "Mora"}).json()
    v3 = client.put("/app/agent-profile", headers=bearer(uid), json={"tone": "formal"}).json()
    assert (v2["version"], v3["version"]) == (2, 3)
    # Guardar sin cambios no crea versión; cambiar sólo el link tampoco (no es comportamiento).
    same = client.put("/app/agent-profile", headers=bearer(uid), json={"tone": "formal"}).json()
    assert same["version"] == 3
    slug = client.put("/app/agent-profile", headers=bearer(uid), json={"public_slug": "versionada-tienda"}).json()
    assert slug["version"] == 3
    versions = client.get("/app/agent-profile/versions", headers=bearer(uid)).json()
    assert [v["version"] for v in versions] == [3, 2, 1]
    restored = client.post("/app/agent-profile/versions/1/restore", headers=bearer(uid)).json()
    assert restored["version"] == 4 and restored["seller_name"] == v1["seller_name"]
    assert restored["tone"] == v1["tone"] and restored["public_slug"] == "versionada-tienda"
    assert client.post("/app/agent-profile/versions/99/restore", headers=bearer(uid)).status_code == 404


def test_versions_are_isolated(accounts):
    client = TestClient(app)
    uid_a, _ = accounts("Uno")
    uid_b, _ = accounts("Dos")
    client.put("/app/agent-profile", headers=bearer(uid_a), json={"seller_name": "Ana"})
    client.get("/app/agent-profile", headers=bearer(uid_b))
    assert [v["version"] for v in client.get("/app/agent-profile/versions", headers=bearer(uid_b)).json()] == [1]
    assert client.post("/app/agent-profile/versions/2/restore", headers=bearer(uid_b)).status_code == 404


def test_reply_records_profile_version(shop, raw_conn):
    _profile(shop, seller_name="Lu")
    chat = Chat(shop["tenant"])
    chat.say("canilla negra")
    with raw_conn.cursor() as cur:
        cur.execute("select profile_version from messages where conversation_id = %s and direction = 'outbound'",
                    (chat.conv,))
        assert cur.fetchone()["profile_version"] == 2
    raw_conn.commit()


# --- Políticas ------------------------------------------------------------------------
def test_minimum_order_is_enforced_by_the_domain(shop):
    _profile(shop, policies={"min_order_total": 20000})
    conv = new_conversation(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["flex"], 1)              # $6.800
    res = orders.checkout(shop["tenant"], conv)
    assert res.status == "below_minimum" and res.shortage["minimum"] == 20000
    orders.add_item(shop["tenant"], conv, shop["flex"], 2)              # $20.400
    assert orders.checkout(shop["tenant"], conv).status == "pending_payment"


def test_agent_explains_minimum_and_never_asks_to_confirm(shop):
    _profile(shop, policies={"min_order_total": 20000})
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    r = chat.say("la compro")
    assert "compra mínima es de $20.000" in r and "¿Confirmás?" not in r


def test_human_only_category_never_enters_the_cart(shop):
    _profile(shop, policies={"human_only_categories": ["Repuestos"]})
    conv = new_conversation(shop["tenant"])
    assert orders.add_item(shop["tenant"], conv, shop["flex"], 1).status == "requires_human"
    assert orders.add_item(shop["tenant"], conv, shop["mono_aq"], 1).status == "ok"


def test_human_only_policy_added_after_cart_blocks_checkout(shop):
    conv = new_conversation(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["flex"], 1)
    _profile(shop, policies={"human_only_categories": ["repuestos"]})
    assert orders.checkout(shop["tenant"], conv).status == "requires_human"


def test_delivery_zones_answer_from_policy(shop):
    _profile(shop, policies={"delivery_zones": "CABA, Rosario"}, shipping="Costo según zona.")
    chat = Chat(shop["tenant"])
    assert "Sí, enviamos a Rosario" in chat.say("hacen envíos a rosario?")
    assert chat.last.trace[0]["name"] == "consultar_envio"


def test_policy_validation():
    with pytest.raises(ValueError):
        agent_profile.validate({"policies": {"min_order_total": -1}})
    with pytest.raises(ValueError):
        agent_profile.validate({"disabled_tools": ["borrar_todo"]})
    assert agent_profile.validate({"policies": {"min_order_total": "", "delivery_zones": " , "}}) == {"policies": {}}


# --- Herramientas por negocio --------------------------------------------------------------
def test_disabling_direct_sale_turns_checkout_into_a_lead(shop):
    _profile(shop, disabled_tools=["preparar_compra"])
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    r = chat.say("la compro")
    assert "te contacta una persona" in r and chat.last.requires_human
    assert chat.say("sí") and orders.conversation_orders(shop["tenant"], chat.conv) == []


def test_disabling_order_status(shop):
    _profile(shop, disabled_tools=["estado_pedido"])
    chat = Chat(shop["tenant"])
    assert "te lo confirma una persona" in chat.say("¿cómo va mi pedido?")


def test_yes_after_direct_sale_is_disabled_creates_no_order(shop):
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    assert "¿Confirmás?" in chat.say("la compro")          # resumen con la venta habilitada
    _profile(shop, disabled_tools=["preparar_compra"])     # el dueño la apaga antes del "sí"
    r = chat.say("sí")
    assert "te contacta una persona" in r and orders.conversation_orders(shop["tenant"], chat.conv) == []


def test_buy_intent_wins_over_documents_in_rules_mode(shop):
    from app.domain import knowledge
    with tenant_tx(shop["tenant"]) as cur:
        knowledge.add_document(cur, shop["tenant"], "Instalación", "Para instalar la canilla se usa teflón.")
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    r = chat.say("lo compro, ¿se puede instalar fácil?")
    assert "¿Confirmás?" in r and "teflón" not in r


def test_product_request_with_a_document_word_searches_products(shop):
    from app.domain import knowledge
    with tenant_tx(shop["tenant"]) as cur:
        knowledge.add_document(cur, shop["tenant"], "Garantías", "La garantía de las canillas es de 5 años.")
    r = Chat(shop["tenant"]).say("busco canilla negra con garantía")
    assert "$89.900" in r and "5 años" not in r
