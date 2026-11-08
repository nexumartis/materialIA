"""WhatsApp etapa 1: conexión de un local, firma de Meta, envío y mensajes entrantes.
Meta se simula con httpx.MockTransport (sin red). Plan: docs/superpowers/plans/2026-11-08-whatsapp-etapa1.md."""
from __future__ import annotations

import hashlib
import hmac

import pytest
from cryptography.fernet import Fernet

from app import whatsapp
from app.config import settings
from conftest import TENANT_C, TENANT_D

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
