"""Aislamiento a nivel base (0003_accounts): bajo el rol `app_user` (sin BYPASSRLS) un
usuario sólo ve y modifica datos del negocio de su membresía, y no puede cambiarse de
empresa ni ampliar su acceso con la GUC del sandbox."""
from __future__ import annotations

import psycopg
import pytest

from conftest import TENANT_D, seed_opportunity


def _as_app_user(conn, uid: str | None, sql: str, params: tuple = (), extra_gucs: dict | None = None):
    """Corre `sql` como app_user con app.current_uid=uid. Siempre hace rollback."""
    try:
        with conn.cursor() as cur:
            cur.execute("set local role app_user")
            if uid is not None:
                cur.execute("select set_config('app.current_uid', %s, true)", (uid,))
            for k, v in (extra_gucs or {}).items():
                cur.execute("select set_config(%s, %s, true)", (k, v))
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else cur.rowcount
    finally:
        conn.rollback()


def test_signup_provisions_one_tenant_and_owner_membership(raw_conn, accounts):
    uid, tid = accounts("Vidriería Té")
    with raw_conn.cursor() as cur:
        cur.execute("select name from tenants where id = %s", (tid,))
        assert cur.fetchone()["name"] == "Vidriería Té"
        cur.execute("select tenant_id, role from memberships where user_id = %s", (uid,))
        rows = cur.fetchall()
    assert [(str(r["tenant_id"]), r["role"]) for r in rows] == [(tid, "owner")]


@pytest.mark.parametrize("name", [None, "", "   "])
def test_signup_without_business_name_uses_default(raw_conn, accounts, name):
    _, tid = accounts(name)
    with raw_conn.cursor() as cur:
        cur.execute("select name from tenants where id = %s", (tid,))
        assert cur.fetchone()["name"] == "Mi negocio"


def test_user_sees_exactly_own_opportunities_and_tenant(raw_conn, accounts):
    uid_a, t_a = accounts("A")
    _, t_b = accounts("B")
    opp_a = seed_opportunity(raw_conn, t_a)
    seed_opportunity(raw_conn, t_b)
    rows = _as_app_user(raw_conn, uid_a, "select id from opportunities")
    assert {str(r["id"]) for r in rows} == {opp_a}
    rows = _as_app_user(raw_conn, uid_a, "select id from tenants")
    assert {str(r["id"]) for r in rows} == {t_a}


def test_user_cannot_update_foreign_opportunity(raw_conn, accounts):
    uid_a, _ = accounts("A")
    _, t_b = accounts("B")
    opp_b = seed_opportunity(raw_conn, t_b)
    n = _as_app_user(raw_conn, uid_a, "update opportunities set stage = 'cerrada' where id = %s", (opp_b,))
    assert n == 0


def test_user_cannot_move_own_opportunity_to_other_tenant(raw_conn, accounts):
    uid_a, t_a = accounts("A")
    _, t_b = accounts("B")
    opp_a = seed_opportunity(raw_conn, t_a)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a, "update opportunities set tenant_id = %s where id = %s", (t_b, opp_a))


def test_user_cannot_log_activity_in_other_tenant(raw_conn, accounts):
    uid_a, _ = accounts("A")
    _, t_b = accounts("B")
    opp_b = seed_opportunity(raw_conn, t_b)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a,
                     "insert into opportunity_activity (tenant_id, opportunity_id, kind) values (%s, %s, 'nota')",
                     (t_b, opp_b))


def test_user_cannot_write_audit_for_other_tenant(raw_conn, accounts):
    uid_a, t_a = accounts("A")
    _, t_b = accounts("B")
    assert _as_app_user(raw_conn, uid_a,
                        "insert into audit_events (tenant_id, event_type) values (%s, 'probe')", (t_a,)) == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a, "insert into audit_events (tenant_id, event_type) values (%s, 'probe')", (t_b,))


def test_user_cannot_change_own_membership(raw_conn, accounts):
    uid_a, _ = accounts("A")
    _, t_b = accounts("B")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a, "update memberships set tenant_id = %s where user_id = %s", (t_b, uid_a))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a, "insert into memberships (user_id, tenant_id) values (%s, %s)", (uid_a, t_b))


def test_user_cannot_create_or_edit_tenants(raw_conn, accounts):
    uid_a, t_a = accounts("A")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a, "insert into tenants (name) values ('intruso')")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _as_app_user(raw_conn, uid_a, "update tenants set name = 'x' where id = %s", (t_a,))


def test_sandbox_guc_does_not_widen_access(raw_conn, accounts):
    uid_a, t_a = accounts("A")
    opp_a = seed_opportunity(raw_conn, t_a)
    rows = _as_app_user(raw_conn, uid_a, "select id from opportunities",
                        extra_gucs={"app.current_tenant": TENANT_D})
    assert {str(r["id"]) for r in rows} == {opp_a}


def test_no_uid_sees_nothing(raw_conn, accounts):
    _, t_a = accounts("A")
    opp = seed_opportunity(raw_conn, t_a)
    with raw_conn.cursor() as cur:
        cur.execute("insert into opportunity_activity (tenant_id, opportunity_id, kind) "
                    "values (%s, %s, 'nota')", (t_a, opp))
        for table in ("opportunities", "opportunity_activity", "tenants", "memberships"):
            cur.execute(f"select 1 from {table} limit 1")
            assert cur.fetchone(), f"{table} vacía como postgres: el assert de abajo sería vacuo"
    raw_conn.commit()
    for table in ("opportunities", "opportunity_activity", "tenants", "memberships"):
        assert _as_app_user(raw_conn, None, f"select 1 from {table}") == []


def test_app_user_has_no_access_to_out_of_scope_tables(raw_conn, accounts):
    uid_a, _ = accounts("A")
    for table in ("catalog_items", "price_entries", "conversations", "messages", "demo_customers"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _as_app_user(raw_conn, uid_a, f"select 1 from {table}")


def test_activity_cannot_point_to_foreign_opportunity(raw_conn, accounts):
    """Referencial por empresa: actividad de A no puede colgar de una oportunidad de B."""
    uid_a, t_a = accounts("A")
    _, t_b = accounts("B")
    opp_b = seed_opportunity(raw_conn, t_b)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _as_app_user(raw_conn, uid_a,
                     "insert into opportunity_activity (tenant_id, opportunity_id, kind) values (%s, %s, 'nota')",
                     (t_a, opp_b))


def test_helpers_not_executable_by_postgrest_roles(raw_conn):
    with raw_conn.cursor() as cur:
        for fn in ("app_uid()", "app_member_tenant()", "handle_new_user()"):
            for role in ("anon", "authenticated"):
                cur.execute("select has_function_privilege(%s, %s, 'execute') as ok", (role, fn))
                assert cur.fetchone()["ok"] is False, f"{role} puede ejecutar {fn}"
