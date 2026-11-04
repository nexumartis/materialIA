"""Integración preparada para DB dedicada; no ejecutar contra una DB compartida."""
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from app import audio, buyer_session
from app.config import settings
from app.domain import opportunities
from app.main import app
from conftest import TENANT_C, TENANT_D

SLUG = "sanitarios-demo-c"
MP3 = b"\xff\xfb\x90\x64" + b"\0" * 128


@pytest.fixture(autouse=True)
def audio_environment(monkeypatch, raw_conn):
    values = {
        "audio_demo_enabled": True, "audio_demo_tenant": TENANT_C,
        "audio_api_key": "synthetic-key", "audio_voice_id": "synthetic-voice",
        "audio_ip_per_minute": 1000, "audio_conversation_per_hour": 1000,
        "audio_daily_calls_per_tenant": 1000, "audio_daily_calls_global": 1000,
        "audio_daily_stt_bytes_per_tenant": 1_000_000,
        "audio_daily_stt_bytes_global": 1_000_000,
        "audio_daily_tts_characters_per_tenant": 1_000_000,
        "audio_daily_tts_characters_global": 1_000_000,
        "audio_max_tts_characters": 2000,
        "audio_max_response_bytes": 1_000_000,
        "audio_provider_timeout_seconds": 20.0,
        "trusted_proxy_hops": 0,
    }
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)
    prefix = "audio-test-" + uuid.uuid4().hex
    monkeypatch.setattr(audio, "BUCKET_PREFIX", prefix)
    calls = []

    async def handle(request):
        await request.aread()
        calls.append(request)
        return httpx.Response(200, content=MP3, headers={"content-type": "audio/mpeg"})

    monkeypatch.setattr(audio, "provider_client", lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handle), trust_env=False,
    ))
    yield calls, prefix
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        cur.execute("delete from rate_limits where bucket like %s", (prefix + ":%",))
    raw_conn.commit()


@pytest.fixture
def thread(raw_conn):
    made = []

    def make(tenant=TENANT_C):
        conv, token = buyer_session.start(tenant)
        made.append((tenant, conv))
        opportunities.add_message(tenant, conv, "inbound", "Pregunta sintética")
        opportunities.add_message(tenant, conv, "outbound", "Respuesta sintética",
                                  {"quick_replies": []})
        return conv, token

    yield make
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        for tenant, conv in made:
            cur.execute("delete from conversations where tenant_id = %s and id = %s", (tenant, conv))
    raw_conn.commit()


def test_message_ids_are_additive_persisted_and_stable(thread, raw_conn):
    conv, token = thread()
    client = TestClient(app)
    url = f"/public/{SLUG}/conversations/{conv}"
    headers = {"X-Conversation-Token": token}
    first = client.get(url, headers=headers)
    assert first.status_code == 200
    messages = first.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert [m["content"] for m in messages] == ["Pregunta sintética", "Respuesta sintética"]
    assert messages[1]["ui"] == {"quick_replies": []}
    ids = [m["id"] for m in messages]
    assert len(set(ids)) == 2 and all(str(uuid.UUID(mid)) == mid for mid in ids)
    assert client.get(url, headers=headers).json()["messages"] == messages
    with raw_conn.cursor() as cur:
        cur.execute("select id from messages where tenant_id = %s and conversation_id = %s",
                    (TENANT_C, conv))
        assert {str(row["id"]) for row in cur.fetchall()} == set(ids)
    raw_conn.rollback()


def test_tts_permissions_use_real_ownership_and_tenant_scoped_message_query(thread, audio_environment):
    calls, _ = audio_environment
    conv, token = thread()
    other_conv, other_token = thread()
    foreign_conv, _ = thread(TENANT_D)
    messages = opportunities.conversation_messages(TENANT_C, conv)
    inbound, outbound = messages[0]["id"], messages[1]["id"]
    other_mid = opportunities.conversation_messages(TENANT_C, other_conv)[1]["id"]
    foreign_mid = opportunities.conversation_messages(TENANT_D, foreign_conv)[1]["id"]
    client = TestClient(app)

    def url(mid):
        return f"/public/{SLUG}/conversations/{conv}/messages/{mid}/audio"

    for supplied in (None, "invalid", other_token):
        headers = {"X-Conversation-Token": supplied} if supplied else {}
        assert client.post(url(outbound), headers=headers).status_code == 404
    headers = {"X-Conversation-Token": token}
    for mid in (inbound, other_mid, foreign_mid, str(uuid.uuid4())):
        assert client.post(url(mid), headers=headers).status_code == 404
    assert calls == []
    assert client.post(url(outbound), headers=headers).content == MP3
    assert len(calls) == 1


def test_atomic_shared_reservation_allows_only_one_concurrent_call(
        monkeypatch, raw_conn, audio_environment):
    _, prefix = audio_environment
    monkeypatch.setattr(settings, "audio_daily_calls_per_tenant", 1)
    monkeypatch.setattr(settings, "audio_daily_calls_global", 1)

    def attempt(index):
        try:
            audio.reserve(TENANT_C, f"synthetic-ip-{index}", None, "stt", 1)
            return True
        except audio.LimitExceeded:
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(attempt, range(16)))
    assert sum(results) == 1
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) as n, sum(hits) as total from rate_limits where bucket like %s",
                    (prefix + ":%",))
        row = cur.fetchone()
    raw_conn.rollback()
    # IP + llamadas tenant/global + bytes tenant/global: ningún incremento parcial de los rechazados.
    assert row["n"] == 5 and row["total"] == 5


@pytest.mark.parametrize("field,kind", [
    ("audio_daily_stt_bytes_per_tenant", "stt"),
    ("audio_daily_stt_bytes_global", "stt"),
    ("audio_daily_tts_characters_per_tenant", "tts"),
    ("audio_daily_tts_characters_global", "tts"),
    ("audio_daily_calls_per_tenant", "stt"),
    ("audio_daily_calls_global", "tts"),
])
def test_daily_unit_and_call_limits_roll_back_the_entire_rejected_reservation(
        field, kind, monkeypatch, raw_conn, audio_environment):
    _, prefix = audio_environment
    monkeypatch.setattr(settings, field, 1)
    audio.reserve(TENANT_C, "first-ip", None, kind, 1)
    with pytest.raises(audio.LimitExceeded):
        audio.reserve(TENANT_C, "second-ip", None, kind, 1)
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) as n, sum(hits) as total from rate_limits where bucket like %s",
                    (prefix + ":%",))
        row = cur.fetchone()
    raw_conn.rollback()
    assert row["n"] == 5 and row["total"] == 5


@pytest.mark.parametrize("axis", ["ip", "conversation"])
def test_ip_and_conversation_limits_are_shared_across_stt_and_tts(axis, monkeypatch):
    monkeypatch.setattr(settings, "audio_ip_per_minute", 1 if axis == "ip" else 1000)
    monkeypatch.setattr(settings, "audio_conversation_per_hour", 1 if axis == "conversation" else 1000)
    audio.reserve(TENANT_C, "first-ip", "first-conversation", "stt", 1)
    with pytest.raises(audio.LimitExceeded):
        audio.reserve(TENANT_C, "first-ip" if axis == "ip" else "second-ip",
                      "first-conversation" if axis == "conversation" else "second-conversation", "tts", 1)


def test_global_budget_is_shared_between_tenants(monkeypatch):
    monkeypatch.setattr(settings, "audio_daily_calls_global", 2)
    audio.reserve(TENANT_C, "c-ip", None, "stt", 1)
    audio.reserve(TENANT_D, "d-ip", None, "tts", 1)
    with pytest.raises(audio.LimitExceeded):
        audio.reserve(TENANT_D, "another-ip", None, "stt", 1)


def test_panel_sandbox_audio_speaks_sandbox_replies_but_never_public_conversations(thread, audio_environment):
    calls, _ = audio_environment
    client = TestClient(app)
    assert client.get("/sandbox/sales/audio?company=C").json()["enabled"] is True
    assert client.get("/sandbox/sales/audio?company=D").json()["enabled"] is False
    chat = client.post("/sandbox/sales/chat?company=C", json={"message": "hola"}).json()
    conv = chat["conversation_id"]
    bot = [m for m in client.get(f"/sandbox/sales/{conv}?company=C").json()["messages"]
           if m["role"] != "user"][-1]
    r = client.post(f"/sandbox/sales/{conv}/messages/{bot['id']}/audio?company=C")
    assert r.status_code == 200 and r.content == MP3 and len(calls) == 1
    public_conv, _ = thread()
    public_msg = opportunities.conversation_messages(TENANT_C, public_conv)[-1]["id"]
    r = client.post(f"/sandbox/sales/{public_conv}/messages/{public_msg}/audio?company=C")
    assert r.status_code == 404 and len(calls) == 1      # el panel no es puerta a la tienda
    assert client.post(f"/sandbox/sales/{conv}/messages/{bot['id']}/audio?company=D").status_code == 404
