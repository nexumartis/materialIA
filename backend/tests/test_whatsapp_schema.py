"""WhatsApp (0034): una conversación por contacto y la cola de salida que llena el trigger de `messages`."""
from __future__ import annotations

import json

import psycopg
import pytest

from conftest import TENANT_C


_CREATED: list[str] = []


def _conv(conn, tenant: str, wa_id: str | None) -> str:
    with conn.cursor() as cur:
        cur.execute("insert into conversations (tenant_id, channel, status, wa_id) values (%s, %s, 'open', %s) "
                    "returning id", (tenant, "whatsapp" if wa_id else "web", wa_id))
        conv = str(cur.fetchone()["id"])
    conn.commit()
    _CREATED.append(conv)
    return conv


def _msg(conn, tenant: str, conv: str, direction: str, content: str, payload: dict | None) -> str:
    with conn.cursor() as cur:
        cur.execute("insert into messages (tenant_id, conversation_id, direction, content, payload) "
                    "values (%s, %s, %s, %s, %s::jsonb) returning id",
                    (tenant, conv, direction, content, json.dumps(payload) if payload else None))
        msg = str(cur.fetchone()["id"])
    conn.commit()
    return msg


def _outbox(conn, message_id: str):
    with conn.cursor() as cur:
        cur.execute("select status from whatsapp_outbox where message_id = %s", (message_id,))
        return cur.fetchone()


@pytest.fixture(autouse=True)
def _cleanup(raw_conn):
    yield
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        cur.execute("delete from conversations where id = any(%s::uuid[])", (_CREATED,))
    raw_conn.commit()
    _CREATED.clear()


def test_outbound_en_conversacion_whatsapp_se_encola(raw_conn):
    conv = _conv(raw_conn, TENANT_C, wa_id="5491100000001")
    msg = _msg(raw_conn, TENANT_C, conv, "outbound", "hola", None)
    assert _outbox(raw_conn, msg)["status"] == "pending"


def test_outbound_web_no_se_encola(raw_conn):
    conv = _conv(raw_conn, TENANT_C, wa_id=None)
    msg = _msg(raw_conn, TENANT_C, conv, "outbound", "hola", None)
    assert _outbox(raw_conn, msg) is None


def test_inbound_y_owner_app_no_se_encolan(raw_conn):
    conv = _conv(raw_conn, TENANT_C, wa_id="5491100000002")
    assert _outbox(raw_conn, _msg(raw_conn, TENANT_C, conv, "inbound", "hola", None)) is None
    assert _outbox(raw_conn, _msg(raw_conn, TENANT_C, conv, "outbound", "ya va", {"type": "owner_app"})) is None


def test_un_contacto_una_conversacion(raw_conn):
    _conv(raw_conn, TENANT_C, wa_id="5491100000003")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _conv(raw_conn, TENANT_C, wa_id="5491100000003")
