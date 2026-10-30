"""Bandeja de conversaciones y toma de control humana (roadmap etapa 2).

Derivar ⇒ «derivadas»; tomar ⇒ el agente no responde; responder ⇒ el cliente ve al equipo;
devolver ⇒ el agente vuelve. Aislado por negocio y sin exponer el token del comprador."""
from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop

HDR = "X-Conversation-Token"


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def shop(client, accounts, raw_conn):
    return _shop(client, accounts, raw_conn, "Tienda Bandeja")


def _say(client, shop, text, conv=None, token=None):
    r = client.post(f"/public/{shop['slug']}/chat", json={"message": text, "conversation_id": conv},
                    headers={HDR: token} if token else {})
    assert r.status_code == 200
    j = r.json()
    return j, conv or j["conversation_id"], token or j["conversation_token"]


def _ids(client, owner, filter_="todas"):
    r = client.get(f"/app/inbox?filter={filter_}", headers=owner)
    assert r.status_code == 200
    return [c["id"] for c in r.json()]


def test_handoff_take_reply_and_release(client, shop, raw_conn):
    owner = bearer(shop["uid"])
    _, quiet, _ = _say(client, shop, "¿Qué productos tenés?")
    j, conv, token = _say(client, shop, "quiero hablar con una persona")
    assert j["requires_human"] and "este mismo chat" in j["reply"] and "plazo" in j["reply"]
    assert conv in _ids(client, owner, "derivadas") and quiet not in _ids(client, owner, "derivadas")

    taken = client.post(f"/app/inbox/{conv}/take", headers=owner).json()
    assert taken["taken_by_me"] and taken["needs_human"]
    assert conv in _ids(client, owner, "mias")
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) n from messages where conversation_id = %s and direction = 'outbound'", (conv,))
        before = cur.fetchone()["n"]
    raw_conn.commit()

    # Con la conversación tomada, el agente no responde: el mensaje queda guardado, sin réplica.
    held, _, _ = _say(client, shop, "¿me pasás el precio del flete?", conv, token)
    assert held["reply"] == "" and held["mode"] == "human"
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) n from messages where conversation_id = %s and direction = 'outbound'", (conv,))
        assert cur.fetchone()["n"] == before
    raw_conn.commit()
    assert conv in _ids(client, owner, "sin_responder")

    r = client.post(f"/app/inbox/{conv}/reply", headers=owner, json={"text": "Hola, soy Ana del local. El flete sale $5.000."})
    assert r.status_code == 200 and r.json()["messages"][-1]["author"] == "persona"
    assert conv not in _ids(client, owner, "sin_responder")
    view = client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={HDR: token}).json()
    assert view["attended_by_human"] is True
    assert view["messages"][-1]["ui"] == {"type": "human"} and "Ana" in view["messages"][-1]["content"]

    released = client.post(f"/app/inbox/{conv}/release", headers=owner).json()
    assert not released["taken"] and not released["needs_human"]
    assert conv not in _ids(client, owner, "derivadas")
    back, _, _ = _say(client, shop, "busco una canilla de cocina negra", conv, token)
    assert back["reply"] and back["mode"] != "human"
    assert client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={HDR: token}).json()["attended_by_human"] is False


def test_replying_takes_control_and_orders_filter(client, shop):
    owner = bearer(shop["uid"])
    _, conv, token = _say(client, shop, "canilla de cocina negra")
    _say(client, shop, "agregame la 1", conv, token)
    _say(client, shop, "comprar", conv, token)
    _say(client, shop, "sí", conv, token)
    assert conv in _ids(client, owner, "con_pedido")
    detail = client.get(f"/app/inbox/{conv}", headers=owner).json()
    assert detail["orders"] and detail["orders"][0]["status"] == "PENDING_PAYMENT"
    assert not detail["taken"]
    r = client.post(f"/app/inbox/{conv}/reply", headers=owner, json={"text": "Te lo separo hasta mañana."})
    assert r.json()["taken_by_me"]
    assert _say(client, shop, "gracias", conv, token)[0]["reply"] == ""


def test_other_business_cannot_see_or_touch_the_conversation(client, shop, accounts, raw_conn):
    _, conv, token = _say(client, shop, "quiero hablar con una persona")
    other = _shop(client, accounts, raw_conn, "Otra Tienda Bandeja")
    stranger = bearer(other["uid"])
    assert conv not in _ids(client, stranger)
    assert client.get(f"/app/inbox/{conv}", headers=stranger).status_code == 404
    for action in ("take", "release"):
        assert client.post(f"/app/inbox/{conv}/{action}", headers=stranger).status_code == 404
    assert client.post(f"/app/inbox/{conv}/reply", headers=stranger, json={"text": "hola"}).status_code == 404
    with raw_conn.cursor() as cur:
        cur.execute("select taken_by from conversations where id = %s", (conv,))
        assert cur.fetchone()["taken_by"] is None
        cur.execute("select count(*) n from messages where conversation_id = %s and payload->>'type' = 'human'", (conv,))
        assert cur.fetchone()["n"] == 0
        cur.execute("delete from memberships where user_id = %s", (shop["uid"],))
    raw_conn.commit()
    assert client.get("/app/inbox", headers=bearer(shop["uid"])).status_code == 403


def test_panel_never_sees_the_buyer_token_or_agent_state(client, shop, raw_conn):
    owner = bearer(shop["uid"])
    _, conv, _ = _say(client, shop, "quiero hablar con una persona")
    body = client.get("/app/inbox", headers=owner).text + client.get(f"/app/inbox/{conv}", headers=owner).text
    assert "access_token" not in body and "agent_state" not in body
    with raw_conn.cursor() as cur:   # la base tampoco se los da al rol del panel
        cur.execute("set local role app_user")
        cur.execute("select set_config('app.current_uid', %s, true)", (shop["uid"],))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute("select access_token_hash from conversations where id = %s", (conv,))
    raw_conn.rollback()


@pytest.mark.parametrize("payload, status", [({"text": ""}, 422), ({"text": "x" * 2001}, 422)])
def test_reply_validation(client, shop, payload, status):
    _, conv, _ = _say(client, shop, "hola")
    assert client.post(f"/app/inbox/{conv}/reply", headers=bearer(shop["uid"]), json=payload).status_code == status
    assert client.get("/app/inbox?filter=cualquiera", headers=bearer(shop["uid"])).status_code == 400


# --- Correcciones de la revisión ---------------------------------------------------
def test_sandbox_chat_also_knows_a_person_is_attending(client, raw_conn):
    """Demo del agente (sandbox, empresa C): también avisa la atención humana para releer el chat."""
    from conftest import TENANT_C
    j = client.post("/sandbox/sales/chat?company=C", json={"message": "hola"}).json()
    conv = j["conversation_id"]
    with raw_conn.cursor() as cur:
        cur.execute("insert into auth.users (id, email, aud, role) values (gen_random_uuid(), "
                    "'sandbox-owner-' || gen_random_uuid() || '@test.local', 'authenticated', 'authenticated') "
                    "returning id")
        uid = str(cur.fetchone()["id"])
        cur.execute("update conversations set taken_by = %s where tenant_id = %s and id = %s", (uid, TENANT_C, conv))
    raw_conn.commit()
    try:
        assert client.get(f"/sandbox/sales/{conv}?company=C").json()["attended_by_human"] is True
    finally:
        with raw_conn.cursor() as cur:
            cur.execute("delete from auth.users where id = %s", (uid,))
        raw_conn.commit()


def test_taking_or_releasing_forgets_what_the_agent_left_pending(client, shop, raw_conn):
    owner = bearer(shop["uid"])
    _, conv, _ = _say(client, shop, "hola")

    def state():
        with raw_conn.cursor() as cur:
            cur.execute("select agent_state from conversations where id = %s", (conv,))
            s = cur.fetchone()["agent_state"] or {}
        raw_conn.commit()
        return s

    for action in ("take", "release"):
        with raw_conn.cursor() as cur:
            cur.execute("update conversations set agent_state = coalesce(agent_state, '{}'::jsonb) || "
                        "'{\"offer\": {\"n\": 2}, \"handoff\": true, \"pending\": {\"x\": 1}, \"last_results\": [1]}'::jsonb "
                        "where id = %s", (conv,))
        raw_conn.commit()
        assert client.post(f"/app/inbox/{conv}/{action}", headers=owner).status_code == 200
        s = state()
        assert not {"offer", "handoff", "pending"} & set(s) and s.get("last_results") == [1], action


def test_agent_reply_is_dropped_if_a_person_took_over_mid_turn(shop, raw_conn, monkeypatch):
    from app.agent import sales_agent
    from conftest import new_conversation
    conv = new_conversation(shop["tenant"])
    uid = shop["uid"]
    real = sales_agent._rules_reply

    def slow_turn(turn, text):   # mientras el agente "piensa", el dueño toma la conversación
        with raw_conn.cursor() as cur:
            cur.execute("update conversations set taken_by = %s where id = %s", (uid, conv))
        raw_conn.commit()
        return real(turn, text)
    monkeypatch.setattr(sales_agent, "_rules_reply", slow_turn)
    r = sales_agent.handle_sales_message(shop["tenant"], "busco una canilla de cocina negra", conv)
    assert r.mode == "human" and r.reply == ""
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) n from messages where conversation_id = %s and direction = 'outbound'", (conv,))
        assert cur.fetchone()["n"] == 0
    raw_conn.commit()


def test_long_conversation_shows_its_newest_messages(client, shop, raw_conn):
    _, conv, token = _say(client, shop, "hola")
    with raw_conn.cursor() as cur:
        cur.execute("insert into messages (tenant_id, conversation_id, direction, content, created_at) "
                    "select %s, %s, 'inbound', 'viejo ' || g, now() + g * interval '1 second' "
                    "from generate_series(1, 520) g", (shop["tenant"], conv))
        cur.execute("insert into messages (tenant_id, conversation_id, direction, content, created_at) "
                    "values (%s, %s, 'inbound', 'EL MÁS NUEVO', now() + interval '1 hour')", (shop["tenant"], conv))
    raw_conn.commit()
    detail = client.get(f"/app/inbox/{conv}", headers=bearer(shop["uid"])).json()
    assert len(detail["messages"]) == 500 and detail["messages"][-1]["content"] == "EL MÁS NUEVO"
    buyer = client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={HDR: token}).json()
    assert buyer["messages"][-1]["content"] == "EL MÁS NUEVO"


def test_handoff_reason_distinguishes_a_quote_from_asking_for_a_person(client, shop):
    from app.agent import sales_agent
    owner = bearer(shop["uid"])
    _, conv, _ = _say(client, shop, "hola")

    def reason():
        [item] = [c for c in client.get("/app/inbox?filter=derivadas", headers=owner).json() if c["id"] == conv]
        return item["needs_human_reason"]
    assert sales_agent._finish_turn(shop["tenant"], conv, {}, "lo cotiza el equipo", None, None, "quote")
    assert reason() == "quote"
    assert sales_agent._finish_turn(shop["tenant"], conv, {}, "registrado", None, None, "asked")
    assert reason() == "asked"
    assert sales_agent._finish_turn(shop["tenant"], conv, {}, "otra cotización", None, None, "quote")
    assert reason() == "asked"                     # pedir una persona no se pisa con una cotización
    _, asked, _ = _say(client, shop, "quiero hablar con una persona")
    assert [c["needs_human_reason"] for c in client.get("/app/inbox?filter=derivadas", headers=owner).json()
            if c["id"] == asked] == ["asked"]


def test_nobody_takes_a_conversation_away_from_another_person(client, shop, accounts, raw_conn):
    owner = bearer(shop["uid"])
    uid_b, _ = accounts("Socio B")
    with raw_conn.cursor() as cur:
        cur.execute("update memberships set tenant_id = %s where user_id = %s", (shop["tenant"], uid_b))
    raw_conn.commit()
    partner = bearer(uid_b)
    _, conv, _ = _say(client, shop, "quiero hablar con una persona")
    assert client.post(f"/app/inbox/{conv}/take", headers=owner).status_code == 200
    assert client.post(f"/app/inbox/{conv}/take", headers=partner).status_code == 409
    assert client.post(f"/app/inbox/{conv}/release", headers=partner).status_code == 409
    assert client.post(f"/app/inbox/{conv}/reply", headers=partner, json={"text": "hola"}).status_code == 409
    view = client.get(f"/app/inbox/{conv}", headers=partner).json()
    assert view["taken"] and not view["taken_by_me"]
    assert client.post(f"/app/inbox/{conv}/release", headers=owner).status_code == 200
    assert client.post(f"/app/inbox/{conv}/take", headers=partner).status_code == 200


def test_the_model_never_sees_human_messages_as_its_own(client, shop):
    from app.domain import opportunities
    owner = bearer(shop["uid"])
    _, conv, _ = _say(client, shop, "quiero hablar con una persona")
    client.post(f"/app/inbox/{conv}/reply", headers=owner, json={"text": "Te hago 30% de descuento"})
    history = opportunities.get_recent_messages(shop["tenant"], conv, limit=20)
    assert history and not any("30% de descuento" in m["content"] for m in history)
