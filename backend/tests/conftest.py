"""Fixtures de test. Requieren un Postgres de Supabase accesible con el seed aplicado
(`supabase db reset` o `supabase start` + migraciones + seed). Si la base no está
accesible, los tests se SALTEAN con un motivo claro (no se fingen pasados).
Con `PV_REQUIRE_DB=1` la falta de base FALLA en vez de saltear (evidencia de aceptación)."""
from __future__ import annotations

import json
import os
import sys
import uuid

import pytest

# Permite importar `app` al correr pytest desde backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import connect, db_healthcheck  # noqa: E402

# UUIDs del seed (supabase/seed.sql)
TENANT_A = "0000000a-0000-0000-0000-00000000000a"
TENANT_B = "0000000b-0000-0000-0000-00000000000b"
A_MAMP_160 = "11111111-0000-0000-0000-000000000001"   # corrediza negra, a medida
A_KIT_FIXED = "11111111-0000-0000-0000-000000000007"  # precio fijo vigente
A_SELL_EXPIRED = "11111111-0000-0000-0000-000000000009"  # precio vencido
MISSING_ID = "99999999-9999-9999-9999-999999999999"


@pytest.fixture(scope="session", autouse=True)
def _force_mock_llm():
    """Los tests corren en modo mock (deterministas y rápidos), sin importar el .env."""
    from app.config import settings
    settings.llm_provider = "mock"


@pytest.fixture(scope="session", autouse=True)
def _require_db():
    ok, detail = db_healthcheck()
    if not ok:
        if os.environ.get("PV_REQUIRE_DB") == "1":
            pytest.fail(f"Postgres no accesible ({detail}) y PV_REQUIRE_DB=1.")
        pytest.skip(f"Postgres no accesible ({detail}). Corré `supabase start` y "
                    "`supabase db reset` antes de los tests.", allow_module_level=True)


@pytest.fixture
def raw_conn():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


# --- Cuentas (usuario de Supabase Auth + negocio vía trigger de 0003) -----
@pytest.fixture
def accounts(raw_conn):
    """Fábrica de cuentas de prueba. `accounts("Nombre")` -> (user_id, tenant_id).
    Inserta en auth.users como postgres (dispara el provisioning) y limpia al final."""
    created: list[tuple[str, str]] = []

    def make(business_name: str | None = "Negocio de prueba") -> tuple[str, str]:
        uid = str(uuid.uuid4())
        meta = {} if business_name is None else {"business_name": business_name}
        with raw_conn.cursor() as cur:
            cur.execute(
                "insert into auth.users (id, email, raw_user_meta_data, aud, role) "
                "values (%s, %s, %s::jsonb, 'authenticated', 'authenticated')",
                (uid, f"{uid}@test.local", json.dumps(meta)),
            )
            cur.execute("select tenant_id from memberships where user_id = %s", (uid,))
            row = cur.fetchone()
        raw_conn.commit()
        tid = str(row["tenant_id"]) if row else ""
        created.append((uid, tid))
        return uid, tid

    yield make
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        for uid, tid in created:
            cur.execute("delete from auth.users where id = %s", (uid,))
            if tid:
                cur.execute("delete from tenants where id = %s", (tid,))
    raw_conn.commit()


def seed_opportunity(conn, tenant_id: str, stage: str = "nueva") -> str:
    """Inserta una oportunidad como postgres (fuera de RLS) y devuelve su id."""
    with conn.cursor() as cur:
        cur.execute(
            "insert into opportunities (tenant_id, stage, requirements_json) "
            "values (%s, %s, '{\"probe\": \"cuentas\"}'::jsonb) returning id",
            (tenant_id, stage),
        )
        oid = str(cur.fetchone()["id"])
    conn.commit()
    return oid
