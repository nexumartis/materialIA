"""Fixtures de test. Requieren un Postgres de Supabase accesible con el seed aplicado
(`supabase db reset` o `supabase start` + migraciones + seed). Si la base no está
accesible, los tests se SALTEAN con un motivo claro (no se fingen pasados)."""
from __future__ import annotations

import os
import sys

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
def _require_db():
    ok, detail = db_healthcheck()
    if not ok:
        pytest.skip(f"Postgres no accesible ({detail}). Corré `supabase start` y "
                    "`supabase db reset` antes de los tests.", allow_module_level=True)


@pytest.fixture
def raw_conn():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
