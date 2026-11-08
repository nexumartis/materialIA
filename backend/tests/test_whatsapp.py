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
    _exec(raw_conn, "delete from conversations where tenant_id = %s and channel = 'whatsapp'", TENANT_C)
    _exec(raw_conn, "delete from whatsapp_inbound")
    _exec(raw_conn, "delete from whatsapp_connections")
    _exec(raw_conn, "delete from rate_limits where bucket like 'wa-contact:%%'")


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


# --- Tarea 4: ruta de avisos y mensajes entrantes ---------------------------------------------
def _payload(pnid: str, wamid: str, wa_id: str, text, type_: str = "text") -> dict:
    msg = {"from": wa_id, "id": wamid, "timestamp": "1794161074", "type": type_}
    if type_ == "text":
        msg["text"] = {"body": text}
    else:
        msg[type_] = {"id": "media-1", "mime_type": "image/jpeg"}
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551654354", "phone_number_id": pnid},
        "contacts": [{"profile": {"name": "Cliente"}, "wa_id": wa_id}], "messages": [msg]}}]}]}


def _directions(raw_conn, conv: str) -> list[str]:
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        cur.execute("select direction from messages where conversation_id = %s order by created_at", (conv,))
        return [r["direction"] for r in cur.fetchall()]


def _signed(body: bytes) -> dict:
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest(),
            "Content-Type": "application/json"}


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_verificacion_get(client, wa_settings):
    ok = {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "42"}
    r = client.get("/channels/whatsapp/webhook", params=ok)
    assert r.status_code == 200 and r.text == "42"
    assert client.get("/channels/whatsapp/webhook", params={**ok, "hub.verify_token": "x"}).status_code == 403


def test_post_firma_invalida_403(client, wa_settings):
    r = client.post("/channels/whatsapp/webhook", content=b"{}", headers={"X-Hub-Signature-256": "sha256=00"})
    assert r.status_code == 403


def test_post_firmado_lo_procesa(client, wa_settings, sent, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    body = json.dumps(_payload("PNID-C", "wamid.http", "5491100000016", "hola")).encode()
    r = client.post("/channels/whatsapp/webhook", content=body, headers=_signed(body))
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert _directions(raw_conn, whatsapp.conversation_for(TENANT_C, "5491100000016")) == ["inbound", "outbound"]


def test_texto_lo_contesta_el_agente(wa_settings, sent, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    assert whatsapp.process_payload(_payload("PNID-C", "wamid.1", "5491100000010", "hola, tienen canillas?")) == 1
    conv = whatsapp.conversation_for(TENANT_C, "5491100000010")
    assert _directions(raw_conn, conv) == ["inbound", "outbound"]
    assert sent[0]["to"] == "5491100000010"


def test_mismo_wamid_dos_veces_una_respuesta(wa_settings, sent):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    p = _payload("PNID-C", "wamid.dup", "5491100000011", "hola")
    whatsapp.process_payload(p)
    whatsapp.process_payload(p)
    assert len(sent) == 1


def test_numero_no_conectado_se_ignora(wa_settings, sent, raw_conn):
    assert whatsapp.process_payload(_payload("PNID-NADIE", "wamid.2", "5491100000012", "hola")) == 0
    assert sent == []
    assert _row(raw_conn, "select count(*) n from conversations where wa_id = %s", "5491100000012")["n"] == 0


def test_tope_por_contacto(wa_settings, sent, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_per_contact_hour", 2)
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    for i in range(4):
        whatsapp.process_payload(_payload("PNID-C", f"wamid.f{i}", "5491100000013", "hola"))
    assert len(sent) == 2


def test_redactar_conversacion_borra_el_numero(wa_settings, sent, raw_conn):
    from app.db import tenant_tx
    from app.domain import privacy
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    whatsapp.process_payload(_payload("PNID-C", "wamid.r", "5491100000015", "hola"))
    conv = whatsapp.conversation_for(TENANT_C, "5491100000015")
    with tenant_tx(TENANT_C) as cur:
        privacy.redact_conversation(cur, TENANT_C, "00000000-0000-0000-0000-000000000001", conv)
    raw_conn.rollback()
    assert _row(raw_conn, "select wa_id from conversations where id = %s", conv)["wa_id"] is None


def test_imagen_respuesta_amable(wa_settings, sent):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    whatsapp.process_payload(_payload("PNID-C", "wamid.3", "5491100000014", None, type_="image"))
    assert sent[0]["text"]["body"] == whatsapp.UNSUPPORTED_REPLY


def test_estado_failed_de_meta_marca_la_cola(wa_settings, sent, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000017")
    opportunities.add_message(TENANT_C, conv, "outbound", "hola")
    whatsapp.deliver_due(conversation_id=conv)
    status = {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": f"PNID-{TENANT_C}"},
        "statuses": [{"id": "wamid.out.1", "status": "failed", "recipient_id": "5491100000017",
                      "errors": [{"code": 131031, "title": "Business Account locked"}]}]}}]}]}
    whatsapp.process_payload(status)
    raw_conn.rollback()
    row = _row(raw_conn, "select status, last_error from whatsapp_outbox where conversation_id = %s", conv)
    assert row["status"] == "failed" and "131031" in row["last_error"]


# --- Revisión final: arreglos -----------------------------------------------------------------
def _multi(pnid: str, wa_id: str, items: list[tuple[str, str]]) -> dict:
    """Un aviso con varios mensajes de texto del mismo contacto: [(wamid, texto), …]."""
    p = _payload(pnid, items[0][0], wa_id, items[0][1])
    msgs = p["entry"][0]["changes"][0]["value"]["messages"]
    for wamid, text in items[1:]:
        msgs.append({**msgs[0], "id": wamid, "text": {"body": text}})
    return p


def test_rafaga_del_mismo_contacto_no_corre_turnos_en_paralelo(wa_settings, sent, monkeypatch):
    import threading
    import time as _time
    from app.agent import sales_agent
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    state = {"active": 0, "max": 0, "calls": 0}
    guard = threading.Lock()

    def slow_turn(tenant, text, conv, channel="web_sandbox"):
        with guard:
            state["active"] += 1
            state["calls"] += 1
            state["max"] = max(state["max"], state["active"])
        _time.sleep(0.2)
        with guard:
            state["active"] -= 1

    monkeypatch.setattr(sales_agent, "handle_sales_message", slow_turn)
    threads = [threading.Thread(target=whatsapp.process_payload,
                                args=(_payload("PNID-C", f"wamid.burst{i}", "5491100000030", "hola"),))
               for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state["calls"] == 3 and state["max"] == 1


def test_un_mensaje_que_falla_no_tira_los_demas(wa_settings, sent, monkeypatch, raw_conn):
    from app.agent import sales_agent
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    seen = []

    def turn(tenant, text, conv, channel="web_sandbox"):
        if text == "rompe":
            raise RuntimeError("falla de prueba")
        seen.append(text)

    monkeypatch.setattr(sales_agent, "handle_sales_message", turn)
    whatsapp.process_payload(_multi("PNID-C", "5491100000031", [("wamid.m1", "rompe"), ("wamid.m2", "sigue")]))
    assert seen == ["sigue"]
    raw_conn.rollback()
    assert _row(raw_conn, "select processed_at from whatsapp_inbound where wamid = %s", "wamid.m1")["processed_at"] is None
    assert _row(raw_conn, "select processed_at from whatsapp_inbound where wamid = %s", "wamid.m2")["processed_at"] is not None


def test_mensaje_fallido_se_reprocesa(wa_settings, sent, monkeypatch, raw_conn):
    from app.agent import sales_agent
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    real = sales_agent.handle_sales_message
    monkeypatch.setattr(sales_agent, "handle_sales_message",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("caída de prueba")))
    whatsapp.process_payload(_payload("PNID-C", "wamid.retry", "5491100000032", "hola"))
    assert sent == []
    monkeypatch.setattr(sales_agent, "handle_sales_message", real)
    _exec(raw_conn, "update whatsapp_inbound set received_at = now() - interval '10 minutes' where wamid = %s",
          "wamid.retry")
    assert whatsapp.retry_unprocessed() == 1
    assert len(sent) == 1
    assert whatsapp.retry_unprocessed() == 0


def test_clave_equivocada_no_cuelga_el_envio(wa_settings, sent, monkeypatch, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000033")
    monkeypatch.setattr(settings, "whatsapp_token_key", Fernet.generate_key().decode())
    opportunities.add_message(TENANT_C, conv, "outbound", "hola")
    whatsapp.deliver_due(conversation_id=conv)
    raw_conn.rollback()
    row = _row(raw_conn, "select status, attempts, last_error from whatsapp_outbox where conversation_id = %s", conv)
    assert sent == [] and row["attempts"] == 1 and row["last_error"] == "InvalidToken"


def test_bandeja_responde_aunque_falle_el_envio(wa_settings, sent, accounts, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    uid, tenant = accounts("Tienda WhatsApp Falla")
    conv = _wa_conv(tenant, "5491100000034")
    monkeypatch.setattr(whatsapp, "deliver_due", lambda **k: (_ for _ in ()).throw(RuntimeError("caída")))
    r = TestClient(app).post(f"/app/inbox/{conv}/reply", headers=bearer(uid), json={"text": "Hola"})
    assert r.status_code == 200


def test_foto_con_la_conversacion_tomada_no_responde(wa_settings, sent, accounts, raw_conn):
    uid, tenant = accounts("Tienda WhatsApp Tomada")
    conv = _wa_conv(tenant, "5491100000035")
    _exec(raw_conn, "update conversations set taken_by = %s, taken_at = now() where id = %s", uid, conv)
    whatsapp.process_payload(_payload(f"PNID-{tenant}", "wamid.taken", "5491100000035", None, type_="image"))
    assert sent == []
    assert _directions(raw_conn, conv) == ["inbound", "inbound"]


def test_reaccion_no_se_responde(wa_settings, sent):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    whatsapp.process_payload(_payload("PNID-C", "wamid.react", "5491100000036", None, type_="reaction"))
    assert sent == []
