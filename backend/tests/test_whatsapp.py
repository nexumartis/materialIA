"""WhatsApp etapa 1: conexión de un local, firma de Meta, envío y mensajes entrantes.
Meta se simula con httpx.MockTransport (sin red). Plan: docs/superpowers/plans/2026-11-08-whatsapp-etapa1.md."""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest
from cryptography.fernet import Fernet

from app import auth, whatsapp
from app.config import settings
from app.domain import opportunities
from conftest import TENANT_C, TENANT_D
from jwt_helpers import KEY, bearer

APP_SECRET = "s3cr3t-de-prueba"
VERIFY = "verify-de-prueba"


def _row(conn, sql: str, *args):
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


def _exec(conn, sql: str, *args) -> None:
    with conn.cursor() as cur:
        cur.execute(sql, args)
    conn.commit()


@pytest.fixture
def wa_settings(monkeypatch, raw_conn):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)
    monkeypatch.setattr(settings, "whatsapp_verify_token", VERIFY)
    monkeypatch.setattr(settings, "whatsapp_token_key", Fernet.generate_key().decode())
    yield
    raw_conn.rollback()
    _exec(raw_conn, "delete from conversations where wa_id is not null")
    _exec(raw_conn, "delete from whatsapp_inbound")
    _exec(raw_conn, "delete from whatsapp_connections")


# --- Tarea 2: firma y conexión -----------------------------------------------------------
def test_firma_valida_e_invalida(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "s3cr3t")
    body = b'{"a":1}'
    good = "sha256=" + hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert whatsapp.verify_signature(body, good)
    assert not whatsapp.verify_signature(body, "sha256=" + "0" * 64)
    assert not whatsapp.verify_signature(body, None)


def test_firma_sin_secreto_configurado(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "")
    body = b"{}"
    assert not whatsapp.verify_signature(body, "sha256=" + hmac.new(b"", body, hashlib.sha256).hexdigest())


def test_connect_cifra_y_resuelve_tenant(wa_settings, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1 555 000 0001", "EAAtoken")
    assert whatsapp.tenant_for("PNID-C") == TENANT_C
    stored = _row(raw_conn, "select token_encrypted from whatsapp_connections where tenant_id = %s", TENANT_C)
    assert "EAAtoken" not in stored["token_encrypted"]
    assert whatsapp._token(TENANT_C) == "EAAtoken"


def test_numero_de_otro_negocio(wa_settings):
    whatsapp.connect(TENANT_C, "PNID-X", "WABA-C", "+1", "t1")
    with pytest.raises(whatsapp.NumberTaken):
        whatsapp.connect(TENANT_D, "PNID-X", "WABA-D", "+1", "t2")


def test_desconectado_no_resuelve(wa_settings, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-OFF", "WABA-C", "+1", "t")
    _exec(raw_conn, "update whatsapp_connections set status = 'disconnected' where tenant_id = %s", TENANT_C)
    assert whatsapp.tenant_for("PNID-OFF") is None


# --- Tarea 3: envío -------------------------------------------------------------------------
class _Sent(list):
    """Cuerpos JSON que el backend le mandó a Meta, en orden; `auth` guarda los headers Authorization."""
    def __init__(self):
        super().__init__()
        self.auth: list[str] = []


def _fake_meta(monkeypatch, status: int) -> _Sent:
    sent = _Sent()

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        sent.auth.append(request.headers.get("authorization", ""))
        if status != 200:
            return httpx.Response(status, json={"error": {"code": 131000, "message": "falla de prueba"}})
        return httpx.Response(200, json={"messages": [{"id": f"wamid.out.{len(sent)}"}]})

    monkeypatch.setattr(whatsapp, "_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    return sent


@pytest.fixture
def sent(monkeypatch):
    return _fake_meta(monkeypatch, 200)


@pytest.fixture
def failing_sent(monkeypatch):
    return _fake_meta(monkeypatch, 500)


def _wa_conv(tenant: str, wa_id: str, token: str = "t") -> str:
    """Negocio conectado + conversación del contacto con un mensaje suyo reciente (ventana abierta)."""
    if whatsapp.tenant_for(f"PNID-{tenant}") is None:
        whatsapp.connect(tenant, f"PNID-{tenant}", "WABA", "+1", token)
    conv = whatsapp.conversation_for(tenant, wa_id)
    opportunities.add_message(tenant, conv, "inbound", "hola")
    return conv


def _outbox_status(conv: str) -> str:
    from app.db import system_tx
    with system_tx() as cur:
        cur.execute("select status from whatsapp_outbox where conversation_id = %s order by created_at desc limit 1",
                    (conv,))
        return cur.fetchone()["status"]


def test_split_text():
    parts = whatsapp.split_text("a" * 5000)
    assert [len(p) for p in parts] == [4096, 904]
    assert whatsapp.split_text("hola") == ["hola"]


def test_split_text_corta_en_salto_de_linea():
    text = "a" * 4000 + "\n" + "b" * 200
    assert whatsapp.split_text(text) == ["a" * 4000, "b" * 200]


def test_conversation_for_es_una_por_contacto(wa_settings):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    assert whatsapp.conversation_for(TENANT_C, "5491100000019") == whatsapp.conversation_for(TENANT_C, "5491100000019")


def test_envio_con_el_token_del_local_y_al_contacto(wa_settings, sent, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000025", token="EAAlocal")
    opportunities.add_message(TENANT_C, conv, "outbound", "hola!")
    assert whatsapp.deliver_due(conversation_id=conv) == 1
    assert sent[0] == {"messaging_product": "whatsapp", "to": "5491100000025", "type": "text", "text": {"body": "hola!"}}
    assert sent.auth[0] == "Bearer EAAlocal"
    row = _row(raw_conn, "select status, wamid from whatsapp_outbox where conversation_id = %s", conv)
    assert row["status"] == "sent" and row["wamid"] == "wamid.out.1"


def test_respuesta_larga_en_partes(wa_settings, sent):
    conv = _wa_conv(TENANT_C, "5491100000020")
    opportunities.add_message(TENANT_C, conv, "outbound", "x" * 5000)
    whatsapp.deliver_due(conversation_id=conv)
    assert [len(m["text"]["body"]) for m in sent] == [4096, 904]


def test_ventana_cerrada_no_se_manda(wa_settings, sent, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000021")
    _exec(raw_conn, "update conversations set last_customer_message_at = now() - interval '25 hours' where id = %s", conv)
    opportunities.add_message(TENANT_C, conv, "outbound", "tu pedido salió")
    whatsapp.deliver_due(conversation_id=conv)
    assert sent == [] and _outbox_status(conv) == "window_closed"


def test_error_de_meta_reintenta_y_despues_falla(wa_settings, failing_sent, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000022")
    opportunities.add_message(TENANT_C, conv, "outbound", "hola")
    for _ in range(len(whatsapp.RETRY_DELAYS_S) + 1):
        assert _outbox_status(conv) == "pending"
        _exec(raw_conn, "update whatsapp_outbox set next_attempt_at = now() where conversation_id = %s", conv)
        whatsapp.deliver_due(conversation_id=conv)
    assert _outbox_status(conv) == "failed"
    assert len(failing_sent) == len(whatsapp.RETRY_DELAYS_S) + 1


def test_link_de_pago_se_agrega(wa_settings, sent):
    conv = _wa_conv(TENANT_C, "5491100000023")
    opportunities.add_message(TENANT_C, conv, "outbound", "Te dejo el link.", {"payment": {"url": "https://pago.test/x"}})
    whatsapp.deliver_due(conversation_id=conv)
    assert sent[0]["text"]["body"].endswith("https://pago.test/x")


def test_respuesta_de_la_bandeja_sale_por_whatsapp(wa_settings, sent, accounts, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    uid, tenant = accounts("Tienda WhatsApp")
    conv = _wa_conv(tenant, "5491100000024")
    r = TestClient(app).post(f"/app/inbox/{conv}/reply", headers=bearer(uid), json={"text": "Hola, soy Juan del local"})
    assert r.status_code == 200
    assert sent[-1]["text"]["body"] == "Hola, soy Juan del local"
