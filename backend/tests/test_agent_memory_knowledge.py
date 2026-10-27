"""Memoria del cliente, compactación, base de conocimiento y evaluaciones por negocio."""
from __future__ import annotations

import json
import secrets

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.agent import compaction, llm_sales
from app.agent.sales_agent import handle_sales_message
from app.db import tenant_tx
from app.domain import agent_profile, customer_memory, evals, knowledge
from app.main import app
from jwt_helpers import KEY, bearer

from conftest import new_conversation

GUIDE = """Garantía de grifería

Todas las canillas tienen 5 años de garantía contra defectos de fabricación. El cartucho cerámico
tiene 2 años. La garantía no cubre sarro ni golpes.

Instalación

Las canillas monocomando se instalan con flexibles de 1/2 pulgada. Recomendamos teflón en las roscas."""


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _profile(tenant, **changes):
    with tenant_tx(tenant) as cur:
        agent_profile._ensure(cur, tenant, "Negocio Test")
        return agent_profile._update(cur, tenant, agent_profile.validate(changes))


def _model(payload):
    return lambda system, user: json.dumps(payload)


# --- Memoria del cliente ------------------------------------------------------------
def test_identity_is_per_business_and_stable(shop, accounts):
    key = secrets.token_urlsafe(24)
    a1 = customer_memory.identify(shop["tenant"], "web", key)
    assert a1 and customer_memory.identify(shop["tenant"], "web", key) == a1
    _, other = accounts("Otro negocio")
    assert customer_memory.identify(other, "web", key) not in (None, a1)   # no se correlaciona
    assert customer_memory.identify(shop["tenant"], "web", "corta") is None


def test_memory_is_distilled_sanitized_and_used_in_the_next_conversation(shop):
    key = secrets.token_urlsafe(24)
    customer = customer_memory.identify(shop["tenant"], "web", key)
    conv = new_conversation(shop["tenant"])
    customer_memory.link_conversation(shop["tenant"], conv, customer)
    handle_sales_message(shop["tenant"], "busco canilla negra para la cocina de mi obra en Rosario", conv)
    facts = customer_memory.refresh(shop["tenant"], customer, model=_model({"facts": [
        "Prefiere grifería negra", "Compra para una obra en Rosario",
        "Pagó $89.900", "Su teléfono es 1155554444", "Prefiere grifería negra"]}))
    assert facts == ["Prefiere grifería negra", "Compra para una obra en Rosario"]   # sin montos ni teléfonos

    # Conversación NUEVA del mismo cliente: el modelo recibe la memoria (orientativa).
    conv2 = new_conversation(shop["tenant"])
    customer_memory.link_conversation(shop["tenant"], conv2, customer)
    seen = {}

    def planner(messages, tools):
        seen["system"] = messages[0]["content"]
        return {"content": "¡Hola de nuevo! ¿Seguimos con la obra?", "tool_calls": []}

    handle_sales_message(shop["tenant"], "hola", conv2, planner=planner)
    assert "Compra para una obra en Rosario" in seen["system"] and "orientativo" in seen["system"]


def test_memory_without_model_uses_deterministic_facts(shop):
    customer = customer_memory.identify(shop["tenant"], "web", secrets.token_urlsafe(24))
    conv = new_conversation(shop["tenant"])
    customer_memory.link_conversation(shop["tenant"], conv, customer)
    handle_sales_message(shop["tenant"], "canillas negras para cocina", conv)
    facts = customer_memory.refresh(shop["tenant"], customer, model=lambda s, u: "no es json")
    assert any("negro" in f and "cocina" in f for f in facts)


def test_customer_history_spans_conversations(shop):
    customer = customer_memory.identify(shop["tenant"], "web", secrets.token_urlsafe(24))
    first = new_conversation(shop["tenant"])
    customer_memory.link_conversation(shop["tenant"], first, customer)
    for m in ("busco flexible 40 cm", "agregame 2", "la compro", "sí"):
        handle_sales_message(shop["tenant"], m, first)
    second = new_conversation(shop["tenant"])
    customer_memory.link_conversation(shop["tenant"], second, customer)
    r = handle_sales_message(shop["tenant"], "quiero lo mismo que la otra vez", second)
    assert "Compras anteriores" in r.reply and "2 × Flexible" in r.reply


def test_forget_me_removes_memory_and_identity(shop):
    key = secrets.token_urlsafe(24)
    customer = customer_memory.identify(shop["tenant"], "web", key)
    conv = new_conversation(shop["tenant"])
    customer_memory.link_conversation(shop["tenant"], conv, customer)
    handle_sales_message(shop["tenant"], "canilla negra", conv)
    customer_memory.refresh(shop["tenant"], customer, model=_model({"facts": ["Prefiere negro"]}))
    assert customer_memory.forget(shop["tenant"], customer)
    assert customer_memory.facts(shop["tenant"], customer) == []
    assert customer_memory.customer_of(shop["tenant"], conv) is None
    assert customer_memory.identify(shop["tenant"], "web", key) != customer       # es otra persona


def test_public_store_links_buyer_key_and_forgets(client=None):
    client = TestClient(app)
    key = secrets.token_urlsafe(24)
    r = client.post("/public/sanitarios-demo-c/chat", json={"message": "hola"},
                    headers={"X-Buyer-Key": key}).json()
    tenant = "0000000c-0000-0000-0000-00000000000c"
    customer = customer_memory.customer_of(tenant, r["conversation_id"])
    assert customer
    assert client.delete("/public/sanitarios-demo-c/me", headers={"X-Buyer-Key": key}).json() == {"forgotten": True}
    assert customer_memory.customer_of(tenant, r["conversation_id"]) is None


# --- Compactación -------------------------------------------------------------------
def test_long_conversation_is_compacted_without_prices(shop, monkeypatch):
    conv = new_conversation(shop["tenant"])
    for i in range(12):
        handle_sales_message(shop["tenant"], f"consulta {i}: canilla negra", conv)
    summary = compaction.compact(shop["tenant"], conv, model=_model(
        {"summary": "Busca canilla negra para cocina; le gustó la Aquaflux de $89.900."}))
    assert summary and "$" not in summary and "[precio]" in summary
    # Repetir sin mensajes nuevos no reprocesa (ni llama al modelo).
    assert compaction.compact(shop["tenant"], conv, model=lambda s, u: (_ for _ in ()).throw(AssertionError())) == summary
    seen = {}

    def planner(messages, tools):
        seen["system"] = messages[0]["content"]
        return {"content": "Dale, sigamos.", "tool_calls": []}

    handle_sales_message(shop["tenant"], "sigamos", conv, planner=planner)
    assert "Resumen de la parte anterior" in seen["system"]


# --- Base de conocimiento -----------------------------------------------------------
def test_chunking_keeps_paragraphs_and_overlaps():
    long = "\n\n".join(f"Párrafo {i}. " + "texto " * 60 for i in range(6))
    chunks = knowledge.chunk(long)
    assert len(chunks) > 1 and all(len(c) <= knowledge.CHUNK_CHARS + knowledge.OVERLAP + 2 for c in chunks)


def test_knowledge_search_is_tenant_scoped_and_answers_in_rules_mode(shop, accounts):
    with tenant_tx(shop["tenant"]) as cur:
        knowledge.add_document(cur, shop["tenant"], "Garantías", GUIDE)
    hits = knowledge.search(shop["tenant"], "¿cuánto dura la garantía de las canillas?")
    assert hits and "5 años" in hits[0]["content"]
    _, other = accounts("Ajeno")
    assert knowledge.search(other, "garantía canillas") == []
    _profile(shop["tenant"])
    r = handle_sales_message(shop["tenant"], "¿qué garantía tienen las canillas?")
    assert "5 años" in r.reply and "Garantías" in r.reply


def test_knowledge_tool_for_the_model_and_hybrid_vectors(shop, monkeypatch):
    # Vectores falsos: el fragmento de instalación es el "más parecido".
    monkeypatch.setattr(knowledge, "embed", lambda texts: [[1.0, 0.0] if "teflón" in t or "rosca" in t
                                                           else [0.0, 1.0] for t in texts])
    with tenant_tx(shop["tenant"]) as cur:
        knowledge.add_document(cur, shop["tenant"], "Guía", GUIDE, knowledge.embed(knowledge.chunk(GUIDE)))
    assert knowledge.search(shop["tenant"], "rosca")    # texto + vector
    calls = iter([{"content": "", "tool_calls": [{"name": "buscar_info_negocio", "arguments": {"consulta": "garantía cartucho"}}]},
                  {"content": "El cartucho tiene 2 años de garantía.", "tool_calls": []}])
    r = handle_sales_message(shop["tenant"], "¿el cartucho tiene garantía?", planner=lambda m, t: next(calls))
    assert r.reply == "El cartucho tiene 2 años de garantía." and r.trace[0]["name"] == "buscar_info_negocio"


def test_disabled_tools_are_not_offered_to_the_model(shop):
    _profile(shop["tenant"], disabled_tools=["buscar_info_negocio", "historial_cliente"])
    offered = {}

    def planner(messages, tools):
        offered["names"] = {t["name"] for t in tools}
        return {"content": "Hola", "tool_calls": []}

    handle_sales_message(shop["tenant"], "hola", planner=planner)
    assert "buscar_info_negocio" not in offered["names"] and "buscar_productos" in offered["names"]


def test_knowledge_panel_api(accounts):
    client = TestClient(app)
    uid, _ = accounts("Con documentos")
    doc = client.post("/app/knowledge", headers=bearer(uid), json={"title": "Garantías", "text": GUIDE}).json()
    assert doc["chunks"] >= 1
    assert [d["title"] for d in client.get("/app/knowledge", headers=bearer(uid)).json()] == ["Garantías"]
    uid_b, _ = accounts("Sin acceso")
    assert client.get("/app/knowledge", headers=bearer(uid_b)).json() == []
    assert client.delete(f"/app/knowledge/{doc['id']}", headers=bearer(uid_b)).status_code == 404
    assert client.delete(f"/app/knowledge/{doc['id']}", headers=bearer(uid)).json() == {"deleted": True}
    assert client.post("/app/knowledge", headers=bearer(uid), json={"title": "", "text": "x"}).status_code == 400


# --- Evaluaciones -------------------------------------------------------------------
def test_evals_run_on_a_draft_and_leave_no_trace(shop, raw_conn):
    _profile(shop["tenant"], faq=[{"q": "¿Hacen envíos?", "a": "Sí, enviamos a todo el país."}])
    cases = [{"message": "hacen envíos?", "expect_contains": ["todo el país"], "expect_not_contains": []},
             {"message": "busco flexible 40 cm\nagregame 1", "expect_contains": ["Total: $6.800"],
              "expect_not_contains": ["$1"]}]
    result = evals.run(shop["tenant"], cases)
    assert result["passed"] == 2, result
    # Borrador que rompe la FAQ: la prueba lo detecta sin guardarlo.
    with tenant_tx(shop["tenant"]) as cur:
        draft = {**agent_profile._get(cur, shop["tenant"]), "faq": []}
    failed = evals.run(shop["tenant"], cases[:1], draft)
    assert failed["passed"] == 0 and failed["results"][0]["failures"]
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) as n from conversations where tenant_id = %s and channel = 'eval'", (shop["tenant"],))
        assert cur.fetchone()["n"] == 0
        cur.execute("select count(*) as n from orders where tenant_id = %s", (shop["tenant"],))
        assert cur.fetchone()["n"] == 0
    raw_conn.commit()


def test_saving_a_profile_that_fails_its_evals_is_blocked(accounts):
    client = TestClient(app)
    uid, _ = accounts("Con pruebas")
    client.put("/app/agent-profile", headers=bearer(uid), json={
        "faq": [{"q": "¿Hacen envíos?", "a": "Sí, a todo el país."}]})
    case = client.post("/app/agent-evals", headers=bearer(uid), json={
        "message": "hacen envíos?", "expect_contains": ["todo el país"]}).json()
    assert client.post("/app/agent-evals/run", headers=bearer(uid), json={}).json()["passed"] == 1
    r = client.put("/app/agent-profile", headers=bearer(uid), json={"faq": [], "require_evals": True})
    assert r.status_code == 409 and "pruebas fallaron" in r.json()["detail"]
    assert client.get("/app/agent-profile", headers=bearer(uid)).json()["faq"]      # no se guardó
    forced = client.put("/app/agent-profile", headers=bearer(uid), json={"faq": []}).json()
    assert forced["faq"] == []
    assert client.delete(f"/app/agent-evals/{case['id']}", headers=bearer(uid)).json() == {"deleted": True}
    assert client.post("/app/agent-evals", headers=bearer(uid), json={"message": "hola"}).status_code == 400


def test_evals_never_reserve_stock_or_create_payments(shop, raw_conn):
    case = {"message": "busco flexible 40 cm\nagregame 1\nla compro\nsí",
            "expect_contains": ["link de pago"], "expect_not_contains": []}
    result = evals.run(shop["tenant"], [case])
    assert result["passed"] == 1, result
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) as n from orders where tenant_id = %s", (shop["tenant"],))
        assert cur.fetchone()["n"] == 0
        cur.execute("select reserved from stock_levels where tenant_id = %s and item_id = %s",
                    (shop["tenant"], shop["flex"]))
        assert cur.fetchone()["reserved"] == 0
        cur.execute("select count(*) as n from payments where tenant_id = %s", (shop["tenant"],))
        assert cur.fetchone()["n"] == 0
    raw_conn.commit()


def test_eval_drafts_apply_their_own_policies(shop):
    with tenant_tx(shop["tenant"]) as cur:
        agent_profile._ensure(cur, shop["tenant"], "Negocio Test")
        draft = {**agent_profile._get(cur, shop["tenant"]),
                 "policies": {"human_only_categories": ["repuestos"], "min_order_total": 50000}}
    case = {"message": "busco flexible 40 cm\nagregame 1", "expect_contains": ["persona"], "expect_not_contains": []}
    assert evals.run(shop["tenant"], [case], draft)["passed"] == 1
    assert evals.run(shop["tenant"], [case])["passed"] == 0          # lo guardado no lo exige


def test_document_prices_are_not_repeated(shop):
    with tenant_tx(shop["tenant"]) as cur:
        knowledge.add_document(cur, shop["tenant"], "Servicios", "La garantía extendida cuesta $15.000 o 20000 pesos.")
    r = handle_sales_message(shop["tenant"], "¿cuánto sale la garantía extendida?")
    assert "15.000" not in r.reply and "20000" not in r.reply and "consultar" in r.reply


def test_memory_sanitizer_drops_personal_data_and_amounts():
    facts = customer_memory.sanitize([
        "Prefiere grifería negra", "Vive en Av. Siempreviva 742", "Pagó 4500 pesos",
        "Su celular es 11 5555 4444", "Compra para una obra", "Mail: x@y.com", "DNI 30.123.456"])
    assert facts == ["Prefiere grifería negra", "Compra para una obra"]


def test_vector_ranking_contributes(shop, monkeypatch):
    # Sin palabras en común: sólo los vectores pueden encontrar el fragmento correcto.
    monkeypatch.setattr(knowledge, "embed", lambda texts: [[1.0, 0.0] if ("cerámico" in t or "zzz" in t)
                                                           else [0.0, 1.0] for t in texts])
    with tenant_tx(shop["tenant"]) as cur:
        knowledge.add_document(cur, shop["tenant"], "Cartuchos", "El cartucho cerámico dura dos años.",
                               knowledge.embed(["El cartucho cerámico dura dos años."]))
        knowledge.add_document(cur, shop["tenant"], "Envíos", "Enviamos los martes.",
                               knowledge.embed(["Enviamos los martes."]))
    hits = knowledge.search(shop["tenant"], "zzz")
    assert hits and hits[0]["title"] == "Cartuchos"


def test_forget_with_unknown_key_creates_nothing():
    client = TestClient(app)
    r = client.delete("/public/sanitarios-demo-c/me", headers={"X-Buyer-Key": secrets.token_urlsafe(24)})
    assert r.json() == {"forgotten": False}
