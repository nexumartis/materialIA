"""Panel autenticado: /app/opportunities* sólo ve y modifica oportunidades del negocio
de la sesión, y cada request corre en UNA transacción con rol app_user."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from app import auth, db
from app.config import settings
from app.domain import opportunities
from app.main import app
from conftest import seed_opportunity
from jwt_helpers import KEY, bearer


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


def _row(conn, sql, params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    conn.commit()
    return row


@pytest.mark.parametrize("method,path", [
    ("get", "/app/opportunities"),
    ("patch", "/app/opportunities/00000000-0000-0000-0000-000000000001"),
    ("get", "/app/opportunities/00000000-0000-0000-0000-000000000001/activity"),
])
def test_app_routes_require_auth(client, method, path):
    assert client.request(method, path, json={}).status_code == 401


def test_list_returns_exactly_own_opportunities(client, raw_conn, accounts):
    uid_a, t_a = accounts("A")
    _, t_b = accounts("B")
    own = {seed_opportunity(raw_conn, t_a), seed_opportunity(raw_conn, t_a)}
    seed_opportunity(raw_conn, t_b)
    r = client.get("/app/opportunities", headers=bearer(uid_a))
    assert r.status_code == 200
    assert {o["id"] for o in r.json()} == own


def test_new_business_starts_empty(client, accounts):
    uid, _ = accounts("Nuevo")
    r = client.get("/app/opportunities", headers=bearer(uid))
    assert r.status_code == 200 and r.json() == []


def test_patch_foreign_opportunity_is_404_and_untouched(client, raw_conn, accounts):
    uid_a, _ = accounts("A")
    _, t_b = accounts("B")
    opp_b = seed_opportunity(raw_conn, t_b)
    before = _row(raw_conn, "select stage, updated_at from opportunities where id = %s", (opp_b,))
    r = client.patch(f"/app/opportunities/{opp_b}", headers=bearer(uid_a), json={"stage": "cerrada"})
    assert r.status_code == 404
    after = _row(raw_conn, "select stage, updated_at from opportunities where id = %s", (opp_b,))
    assert after == before
    n = _row(raw_conn, "select count(*) as n from opportunity_activity where opportunity_id = %s", (opp_b,))
    assert n["n"] == 0


def test_foreign_activity_is_404(client, raw_conn, accounts):
    uid_a, _ = accounts("A")
    _, t_b = accounts("B")
    opp_b = seed_opportunity(raw_conn, t_b)
    assert client.get(f"/app/opportunities/{opp_b}/activity", headers=bearer(uid_a)).status_code == 404


def test_patch_own_logs_activity_and_audit_in_own_tenant(client, raw_conn, accounts):
    uid_a, t_a = accounts("A")
    opp_a = seed_opportunity(raw_conn, t_a)
    r = client.patch(f"/app/opportunities/{opp_a}", headers=bearer(uid_a), json={"stage": "cotizada"})
    assert r.status_code == 200 and r.json()["stage"] == "cotizada"
    act = _row(raw_conn, "select tenant_id::text as t, kind, detail from opportunity_activity "
                         "where opportunity_id = %s", (opp_a,))
    assert act == {"t": t_a, "kind": "cambio_estado", "detail": "nueva → cotizada"}
    aud = _row(raw_conn, "select tenant_id::text as t from audit_events "
                         "where entity_id = %s and event_type = 'panel_opportunity_updated'", (opp_a,))
    assert aud == {"t": t_a}
    timeline = client.get(f"/app/opportunities/{opp_a}/activity", headers=bearer(uid_a)).json()
    assert [a["kind"] for a in timeline] == ["cambio_estado"]


def test_patch_invalid_stage_is_400(client, raw_conn, accounts):
    uid_a, t_a = accounts("A")
    opp_a = seed_opportunity(raw_conn, t_a)
    r = client.patch(f"/app/opportunities/{opp_a}", headers=bearer(uid_a), json={"stage": "inventada"})
    assert r.status_code == 400


def test_failure_mid_request_rolls_back_everything(raw_conn, accounts, monkeypatch):
    uid_a, t_a = accounts("A")
    opp_a = seed_opportunity(raw_conn, t_a)

    def boom(*a, **k):
        raise RuntimeError("falla simulada")
    monkeypatch.setattr(opportunities, "_log_activity", boom)
    r = TestClient(app, raise_server_exceptions=False).patch(
        f"/app/opportunities/{opp_a}", headers=bearer(uid_a), json={"stage": "cerrada"})
    assert r.status_code == 500
    assert _row(raw_conn, "select stage from opportunities where id = %s", (opp_a,))["stage"] == "nueva"


def test_pooled_connection_is_clean_after_user_request(raw_conn, accounts, monkeypatch):
    """Con una sola conexión en el pool, tras una request /app que falla, el próximo uso
    (sandbox) vuelve a ser postgres sin uid: el rol y la GUC no se filtran."""
    pool = ConnectionPool(settings.database_url, min_size=1, max_size=1,
                          kwargs={"row_factory": dict_row}, open=True)
    monkeypatch.setattr(db, "_pool", pool)
    try:
        uid_a, t_a = accounts("A")
        opp_a = seed_opportunity(raw_conn, t_a)
        monkeypatch.setattr(opportunities, "_log_activity", lambda *a, **k: 1 / 0)
        TestClient(app, raise_server_exceptions=False).patch(
            f"/app/opportunities/{opp_a}", headers=bearer(uid_a), json={"stage": "cerrada"})
        with db.tenant_tx(t_a) as cur:
            cur.execute("select current_user as u, current_setting('app.current_uid', true) as uid")
            row = cur.fetchone()
        assert row["u"] == "postgres" and not row["uid"]
    finally:
        pool.close()
