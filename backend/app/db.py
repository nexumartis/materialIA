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
from psycopg_pool import ConnectionPool

from .config import settings

# Pool de conexiones: reusa conexiones abiertas (clave con DB remota/cloud, donde
# abrir una conexión por operación cuesta ~1-2s de handshake). Lazy init.
_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url, min_size=1, max_size=10,
            kwargs={"row_factory": dict_row}, open=True,
        )
    return _pool


def connect() -> psycopg.Connection:
    """Conexión suelta (para checks/tests). El resto usa el pool vía tenant_tx."""
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
    # pool.connection() presta una conexión, abre transacción, commitea al salir
    # sin error (rollback si falla) y la devuelve al pool.
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            # `true` => scope local a la transacción (no se filtra entre usos del pool).
            cur.execute(
                "select set_config('app.current_tenant', %s, true)",
                (str(tenant_id),),
            )
            yield cur


@contextlib.contextmanager
def system_tx() -> Iterator[psycopg.Cursor]:
    """Transacción SIN tenant fijado, sólo para procesos de sistema (webhooks de pago, worker)
    que DERIVAN el negocio de filas de la base (p. ej. el pedido), nunca de un dato externo.
    Cualquier operación de negocio posterior debe usar `tenant_tx` con ese tenant."""
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            yield cur


class NoMembership(Exception):
    """El usuario autenticado no tiene negocio asociado."""


@contextlib.contextmanager
def user_tx(uid: str) -> Iterator[tuple[psycopg.Cursor, str]]:
    """Transacción del panel autenticado, con RLS efectivo.

    Asume `app_user` (sin BYPASSRLS) y fija `app.current_uid` con el `sub` ya verificado;
    el negocio lo deriva la base desde `memberships`. Devuelve `(cursor, tenant_id)`.
    Todo lo de la request (lecturas, escrituras, actividad, auditoría) usa ESTE cursor.
    `set local` y `set_config(..., true)` terminan con el commit/rollback: la conexión
    vuelve al pool sin rol ni uid.
    """
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("set local role app_user")
            cur.execute("select set_config('app.current_uid', %s, true)", (str(uid),))
            cur.execute("select app_member_tenant() as tenant_id")
            row = cur.fetchone()
            if not row or row["tenant_id"] is None:
                raise NoMembership()
            yield cur, str(row["tenant_id"])
