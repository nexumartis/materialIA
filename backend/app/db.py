"""Acceso a Postgres (Supabase). Una conexión por operación, con transacción.

Regla multi-tenant innegociable: el `tenant_id` lo resuelve el servidor y se pasa
explícitamente a cada operación; el cliente/LLM nunca lo elige. Además seteamos
`app.current_tenant` por transacción como defensa en profundidad para las políticas
RLS (ver 0001_init.sql), de cara a una futura exposición con rol restringido.
"""
from __future__ import annotations

import contextlib
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from .config import settings


def connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def db_healthcheck() -> tuple[bool, str]:
    """Devuelve (ok, detalle) sin exponer secretos."""
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("select 1 as ok")
            cur.fetchone()
        return True, "postgres reachable"
    except Exception as exc:  # noqa: BLE001 - reportamos tipo, no credenciales
        return False, f"{type(exc).__name__}"


@contextlib.contextmanager
def tenant_tx(tenant_id: str) -> Iterator[psycopg.Cursor]:
    """Transacción con tenant fijado en el servidor.

    Commitea al salir sin excepción; hace rollback si algo falla.
    """
    conn = connect()
    try:
        with conn:  # maneja commit/rollback
            with conn.cursor() as cur:
                # `true` => scope local a la transacción.
                cur.execute(
                    "select set_config('app.current_tenant', %s, true)",
                    (str(tenant_id),),
                )
                yield cur
    finally:
        conn.close()
