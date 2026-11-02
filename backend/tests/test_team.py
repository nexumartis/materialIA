"""Equipo: invitar por email, entrar como staff al registrarse, permisos del staff y notas internas."""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def signup(raw_conn):
    """Registra un usuario con un email dado (confirmado o no). Limpia al final."""
    made: list[str] = []

    def make(email: str, confirmed: bool = True) -> str:
        uid = str(uuid.uuid4())
        with raw_conn.cursor() as cur:
            cur.execute("insert into auth.users (id, email, raw_user_meta_data, aud, role, email_confirmed_at) "
                        "values (%s, %s, %s::jsonb, 'authenticated', 'authenticated', "
                        "case when %s then now() end)", (uid, email, json.dumps({"business_name": "X"}), confirmed))
        raw_conn.commit()
        made.append(uid)
        return uid

    yield make
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        for uid in made:
            cur.execute("delete from tenants where id in (select tenant_id from memberships where user_id = %s "
                        "and role = 'owner')", (uid,))
            cur.execute("delete from auth.users where id = %s", (uid,))
    raw_conn.commit()


def _email() -> str:
    return f"emp-{uuid.uuid4().hex[:8]}@test.local"


def _membership(raw_conn, uid):
    with raw_conn.cursor() as cur:
        cur.execute("select tenant_id, role from memberships where user_id = %s", (uid,))
        row = cur.fetchone()
    raw_conn.commit()
    return row


def test_invited_email_joins_as_staff_without_own_business(client, accounts, signup, raw_conn):
    owner, tenant = accounts("Dueño Equipo")
    email = _email()
    r = client.post("/app/team/invites", json={"email": email.upper()}, headers=bearer(owner))
    assert r.status_code == 200 and r.json()["invites"][0]["email"] == email
    emp = signup(email)
    m = _membership(raw_conn, emp)
    assert str(m["tenant_id"]) == tenant and m["role"] == "staff"
    me = client.get("/app/me", headers=bearer(emp)).json()
    assert me["tenant_id"] == tenant and me["role"] == "staff"
    team = client.get("/app/team", headers=bearer(owner)).json()
    assert team["invites"] == [] and {x["role"] for x in team["members"]} == {"owner", "staff"}


def test_unconfirmed_signup_joins_only_after_confirming(client, accounts, signup, raw_conn):
    owner, tenant = accounts("Dueño Confirma")
    email = _email()
    client.post("/app/team/invites", json={"email": email}, headers=bearer(owner))
    emp = signup(email, confirmed=False)
    assert _membership(raw_conn, emp) is None          # ni negocio propio ni el ajeno todavía
    with raw_conn.cursor() as cur:
        cur.execute("update auth.users set email_confirmed_at = now() where id = %s", (emp,))
    raw_conn.commit()
    assert str(_membership(raw_conn, emp)["tenant_id"]) == tenant


def test_invite_rejects_existing_account_and_other_business(client, accounts):
    owner_a, _ = accounts("A")
    owner_b, _ = accounts("B")
    r = client.post("/app/team/invites", json={"email": f"{owner_b}@test.local"}, headers=bearer(owner_a))
    assert r.status_code == 400 and "ya tiene una cuenta" in r.json()["detail"]
    email = _email()
    assert client.post("/app/team/invites", json={"email": email}, headers=bearer(owner_a)).status_code == 200
    r = client.post("/app/team/invites", json={"email": email}, headers=bearer(owner_b))
    assert r.status_code == 400 and "otro negocio" in r.json()["detail"]
    assert client.post("/app/team/invites", json={"email": "no-es-email"}, headers=bearer(owner_a)).status_code == 400
    # B no ve ni cancela la invitación de A
    assert client.get("/app/team", headers=bearer(owner_b)).json()["invites"] == []
    assert client.delete(f"/app/team/invites/{email}", headers=bearer(owner_b)).status_code == 404
    assert client.delete(f"/app/team/invites/{email}", headers=bearer(owner_a)).status_code == 200


def test_staff_cannot_touch_money_config_or_team(client, accounts, signup):
    owner, _ = accounts("Dueño Permisos")
    email = _email()
    client.post("/app/team/invites", json={"email": email}, headers=bearer(owner))
    emp = signup(email)
    h = bearer(emp)
    for method, path, body in [
        ("get", "/app/team", None), ("post", "/app/team/invites", {"email": _email()}),
        ("put", "/app/agent-profile", {}), ("post", "/app/catalog/import", {"csv": "x"}),
        ("post", f"/app/orders/{uuid.uuid4()}/confirm-transfer", {"amount": 1, "reference": "x"}),
        ("get", "/app/payments/register.csv?month=2026-11", None), ("get", "/app/ai-usage", None),
    ]:
        r = client.request(method.upper(), path, json=body, headers=h)
        assert r.status_code == 403, (path, r.status_code)
    for path in ("/app/opportunities", "/app/inbox", "/app/orders", "/app/catalog"):
        assert client.get(path, headers=h).status_code == 200, path


def test_remove_member_cuts_access_and_returns_taken_chats(client, accounts, signup, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Tienda Equipo")
    owner = shop["uid"]
    email = _email()
    client.post("/app/team/invites", json={"email": email}, headers=bearer(owner))
    emp = signup(email)
    _, conv, _ = _say(client, shop, "hola")
    assert client.post(f"/app/inbox/{conv}/take", headers=bearer(emp)).status_code == 200
    assert client.delete(f"/app/team/members/{owner}", headers=bearer(owner)).status_code == 404
    assert client.delete(f"/app/team/members/{emp}", headers=bearer(owner)).status_code == 200
    assert client.get("/app/me", headers=bearer(emp)).status_code == 403
    d = client.get(f"/app/inbox/{conv}", headers=bearer(owner)).json()
    assert d["taken"] is False and d["needs_human"]


def test_internal_notes_visible_to_team_not_to_customer_or_other_business(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Tienda Notas")
    owner = shop["uid"]
    other, _ = accounts("Otro Notas")
    j, conv, token = _say(client, shop, "hola, quiero un presupuesto")
    r = client.post(f"/app/inbox/{conv}/notes", json={"body": "Cliente de obra, llamar mañana"}, headers=bearer(owner))
    assert r.status_code == 200 and r.json()["author"] == f"{owner}@test.local"
    assert client.post(f"/app/inbox/{conv}/notes", json={"body": "  "}, headers=bearer(owner)).status_code == 400
    assert client.post(f"/app/inbox/{conv}/notes", json={"body": "x"}, headers=bearer(other)).status_code == 404
    d = client.get(f"/app/inbox/{conv}", headers=bearer(owner)).json()
    assert [n["body"] for n in d["notes"]] == ["Cliente de obra, llamar mañana"]
    pub = client.get(f"/public/{shop['slug']}/conversations/{conv}", headers={"X-Conversation-Token": token})
    assert "llamar mañana" not in pub.text
