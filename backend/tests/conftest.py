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
TENANT_C = "0000000c-0000-0000-0000-00000000000c"   # grifería (agente de ventas)
TENANT_D = "0000000d-0000-0000-0000-00000000000d"   # ferretería (segunda empresa)
C_CANILLA = "33333333-0000-0000-0000-000000000001"  # producto de C (precio fijo vigente)
D_FIXED = "44444444-0000-0000-0000-000000000001"    # precio fijo vigente
D_EXPIRED = "44444444-0000-0000-0000-000000000002"  # precio vencido
D_CUSTOM = "44444444-0000-0000-0000-000000000003"   # a medida
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


# --- Comercio: una empresa de grifería NUEVA por test (stock y pedidos aislados) ---------
_SHOP_ITEMS = [
    # clave, sku, nombre, categoría, modo, specs, precio, stock
    ("mono_aq", "T-COC-MONO-NEG-AQ", "Canilla de cocina monocomando negra mate", "griferia", "fixed",
     {"ambiente": "cocina", "tipo": "monocomando", "color": "negro"}, 89900, 6),
    ("mono_hl", "T-COC-MONO-NEG-HL", "Canilla de cocina monocomando negra con pico extraíble", "griferia",
     "fixed", {"ambiente": "cocina", "tipo": "monocomando", "color": "negro"}, 129000, 3),
    ("last", "T-COC-2LL-NEG", "Canilla de cocina dos llaves negra", "griferia", "fixed",
     {"ambiente": "cocina", "tipo": "dos llaves", "color": "negro"}, 74500, 1),
    ("out", "T-LAV-NEG", "Canilla de lavatorio monocomando negra", "griferia", "fixed",
     {"ambiente": "baño", "tipo": "monocomando", "color": "negro"}, 59900, 0),
    ("alt", "T-LAV-CRO", "Canilla de lavatorio monocomando cromo", "griferia", "fixed",
     {"ambiente": "baño", "tipo": "monocomando", "color": "cromo"}, 52000, 8),
    ("flex", "T-FLEX-40", "Flexible de conexión de agua 40 cm (par)", "repuestos", "fixed",
     {"medida": "40 cm"}, 6800, 40),
    ("custom", "T-INOD", "Inodoro largo blanco (a pedido)", "sanitarios", "custom_quote",
     {"color": "blanco", "ambiente": "baño"}, None, None),
]


@pytest.fixture
def shop(raw_conn):
    """Empresa de prueba con catálogo, precios y stock propios. Devuelve {"tenant", <clave>: id}."""
    tid = str(uuid.uuid4())
    ids: dict[str, str] = {"tenant": tid}
    with raw_conn.cursor() as cur:
        cur.execute("insert into tenants (id, name) values (%s, 'Sanitarios Test (SINTÉTICA)')", (tid,))
        for key, sku, name, cat, mode, specs, price, stock in _SHOP_ITEMS:
            cur.execute(
                "insert into catalog_items (tenant_id, sku, name, category, pricing_mode, specs_json, brand) "
                "values (%s, %s, %s, %s, %s, %s::jsonb, 'Marca Test') returning id",
                (tid, sku, name, cat, mode, json.dumps(specs)),
            )
            iid = str(cur.fetchone()["id"])
            ids[key] = iid
            if price is not None:
                cur.execute("insert into price_entries (tenant_id, item_id, amount, valid_from) "
                            "values (%s, %s, %s, date '2026-01-01')", (tid, iid, price))
            if stock is not None:
                cur.execute("insert into stock_levels (tenant_id, item_id, on_hand) values (%s, %s, %s)",
                            (tid, iid, stock))
    raw_conn.commit()
    yield ids
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        cur.execute("delete from sim_provider_payments where external_ref in "
                    "(select id::text from orders where tenant_id = %s)", (tid,))
        cur.execute("delete from tenants where id = %s", (tid,))
    raw_conn.commit()


def stock_of(conn, tenant_id: str, item_id: str) -> tuple[int, int]:
    """(on_hand, reserved) leídos fuera de la app."""
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("select on_hand, reserved from stock_levels where tenant_id = %s and item_id = %s",
                    (tenant_id, item_id))
        r = cur.fetchone()
    conn.commit()
    return r["on_hand"], r["reserved"]


def new_conversation(tenant_id: str) -> str:
    from app.domain import opportunities
    return opportunities.ensure_conversation(tenant_id, None)
