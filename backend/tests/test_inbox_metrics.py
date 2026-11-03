"""Métricas de la bandeja (derivaciones, primera respuesta del equipo) y respuestas rápidas (sin
montos; las usa el equipo y las administra el dueño)."""
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
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_handoff_metrics(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Métricas")
    h = bearer(shop["uid"])
    _, c1, t1 = _say(client, shop, "quiero hablar con una persona")
    _, c2, _ = _say(client, shop, "necesito hablar con un vendedor")
    with raw_conn.cursor() as cur:         # la primera derivación fue hace 10 minutos
        cur.execute("update handoff_events set created_at = now() - interval '10 minutes' where conversation_id = %s", (c1,))
    raw_conn.commit()
    assert client.post(f"/app/inbox/{c1}/reply", headers=h, json={"text": "Hola, te ayudo yo"}).status_code == 200
    client.post(f"/app/inbox/{c1}/reply", headers=h, json={"text": "¿Seguís ahí?"})       # no cuenta dos veces
    m = client.get("/app/insights?days=7", headers=h).json()["inbox"]
    assert m["handoffs"] == 2 and m["answered"] == 1 and m["waiting_now"] == 1
    assert m["by_reason"] == {"asked": 2} and 9.5 <= m["first_response_minutes_p50"] <= 11
    other, _ = accounts("Otra Métricas")
    assert client.get("/app/insights", headers=bearer(other)).json()["inbox"]["handoffs"] == 0


def test_quick_replies(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Atajos")
    h = bearer(shop["uid"])
    r = client.post("/app/quick-replies", headers=h, json={"title": "Horario", "body": "Abrimos de lunes a viernes."})
    assert r.status_code == 200
    for bad in ({"title": "Precio", "body": "La canilla sale $ 89.900"}, {"title": "", "body": "x"},
                {"title": "Promo", "body": "te la dejo en 50 mil"}):
        assert client.post("/app/quick-replies", headers=h, json=bad).status_code == 400
    assert [q["title"] for q in client.get("/app/quick-replies", headers=h).json()] == ["Horario"]
    # Un empleado las usa pero no las administra; otro negocio no las ve.
    email = f"emp-{uuid.uuid4().hex[:8]}@test.local"
    client.post("/app/team/invites", headers=h, json={"email": email})
    emp = str(uuid.uuid4())
    with raw_conn.cursor() as cur:
        cur.execute("insert into auth.users (id, email, raw_user_meta_data, aud, role, email_confirmed_at) "
                    "values (%s, %s, %s::jsonb, 'authenticated', 'authenticated', now())", (emp, email, json.dumps({})))
    raw_conn.commit()
    try:
        assert len(client.get("/app/quick-replies", headers=bearer(emp)).json()) == 1
        assert client.post("/app/quick-replies", headers=bearer(emp), json={"title": "x", "body": "y"}).status_code == 403
    finally:
        with raw_conn.cursor() as cur:
            cur.execute("delete from auth.users where id = %s", (emp,))
        raw_conn.commit()
    other, _ = accounts("Otra Atajos")
    assert client.get("/app/quick-replies", headers=bearer(other)).json() == []
    assert client.delete(f"/app/quick-replies/{r.json()['id']}", headers=bearer(other)).status_code == 404
