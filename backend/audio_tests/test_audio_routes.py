import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import audio, audio_routes, buyer_session
from app.config import settings
from app.domain import agent_profile, privacy

TENANT = "0000000c-0000-0000-0000-00000000000c"
CONV = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
MESSAGE = "33333333-3333-4333-8333-333333333333"
TOKEN = "synthetic-owner-token"
HDR = {"X-Conversation-Token": TOKEN}
STT = "/public/demo/audio/transcriptions"
TTS = f"/public/demo/conversations/{CONV}/messages/{MESSAGE}/audio"
MP3 = b"\xff\xfb\x90\x64" + b"\0" * 128


@pytest.fixture
def web(monkeypatch, provider):
    calls, respond = provider
    state = {"blocked": False, "budget_error": None,
             "owners": {CONV: TOKEN, OTHER: "other-token"},
             "messages": {(CONV, MESSAGE): "Respuesta persistida sintética"}}
    reservations = []
    monkeypatch.setattr(agent_profile, "tenant_by_slug", lambda slug:
                        {"tenant_id": TENANT, "name": "Demo"} if slug == "demo" else None)
    monkeypatch.setattr(buyer_session, "owns", lambda tenant, conv, token:
                        tenant == TENANT and conv in state["owners"] and state["owners"][conv] == token)
    monkeypatch.setattr(privacy, "is_blocked", lambda tenant, conv: state["blocked"])
    monkeypatch.setattr(audio, "outbound_text", lambda tenant, conv, message:
                        state["messages"].get((conv, message)) if tenant == TENANT else None)

    def reserve(*args):
        if state["budget_error"]:
            raise state["budget_error"]
        reservations.append(args)

    monkeypatch.setattr(audio, "reserve", reserve)

    def reply(request):
        if request.url.path == "/v1/speech-to-text":
            return httpx.Response(200, json={"text": "Transcripción sintética"})
        return httpx.Response(200, content=MP3, headers={"content-type": "audio/mpeg"})

    respond(reply)
    app = FastAPI()
    app.include_router(audio_routes.router)
    with TestClient(app) as client:
        yield client, state, reservations, calls


def test_capabilities_and_first_transcription_do_not_create_a_conversation(web, wav_bytes):
    client, _, reservations, calls = web
    capabilities = client.get("/public/demo/audio")
    assert capabilities.status_code == 200
    assert capabilities.headers["cache-control"] == "no-store"
    assert capabilities.json() == {
        "enabled": True, "input_mime": "audio/wav", "sample_rate_hz": 16000,
        "channels": 1, "sample_width_bits": 16, "max_upload_bytes": 1_000_000,
        "max_duration_seconds": 30, "max_tts_characters": 2000,
        "max_transcript_characters": 2000,
    }
    result = client.post(STT, content=wav_bytes(), headers={"content-type": "audio/wav"})
    assert result.status_code == 200
    assert result.json() == {"text": "Transcripción sintética", "duration_seconds": 0.1}
    assert result.headers["cache-control"] == "no-store"
    assert reservations[0][0] == TENANT and reservations[0][2:] == (None, "stt", len(wav_bytes()))
    assert len(calls) == 1


@pytest.mark.parametrize("name,value", [
    ("audio_demo_enabled", False), ("audio_api_key", ""),
    ("audio_voice_id", ""), ("audio_demo_tenant", ""),
    ("audio_demo_tenant", "0000000d-0000-0000-0000-00000000000d"),
])
def test_disabled_tenant_has_no_provider_requests(web, monkeypatch, wav_bytes, name, value):
    client, _, reservations, calls = web
    monkeypatch.setattr(settings, name, value)
    assert client.get("/public/demo/audio").json()["enabled"] is False
    assert client.post(STT, content=wav_bytes(), headers={"content-type": "audio/wav"}).status_code == 404
    assert client.post(TTS, headers=HDR).status_code == 404
    assert reservations == calls == []


def test_missing_store_is_404(web):
    client, _, reservations, calls = web
    assert client.get("/public/missing/audio").status_code == 404
    assert reservations == calls == []


@pytest.mark.parametrize("token", [None, "", "another-buyer-token"])
def test_conversation_requires_its_token_before_any_provider_spend(web, wav_bytes, token):
    client, _, reservations, calls = web
    headers = {"content-type": "audio/wav"}
    if token is not None:
        headers["X-Conversation-Token"] = token
    assert client.post(STT + f"?conversation_id={CONV}", content=wav_bytes(), headers=headers).status_code == 404
    assert client.post(TTS, headers=headers).status_code == 404
    assert reservations == calls == []


def test_blocked_conversation_cannot_use_audio(web, wav_bytes):
    client, state, reservations, calls = web
    state["blocked"] = True
    assert client.post(STT + f"?conversation_id={CONV}", content=wav_bytes(),
                       headers={**HDR, "content-type": "audio/wav"}).status_code == 403
    assert client.post(TTS, headers=HDR).status_code == 403
    assert reservations == calls == []


@pytest.mark.parametrize("mime,body", [
    ("audio/mpeg", b"ID3"), ("application/octet-stream", b"RIFF"),
    ("audio/wav", b"not wav"), ("multipart/form-data", b"file"),
])
def test_upload_requires_allowed_mime_and_verified_container(web, mime, body):
    client, _, reservations, calls = web
    assert client.post(STT, content=body, headers={"content-type": mime}).status_code == 415
    assert reservations == calls == []


def test_upload_limit_does_not_trust_small_content_length(web, monkeypatch, wav_bytes):
    client, _, reservations, calls = web
    monkeypatch.setattr(settings, "audio_max_upload_bytes", 100)
    response = client.post(STT, content=wav_bytes(), headers={
        "content-type": "audio/wav", "content-length": "1",
    })
    assert response.status_code == 413
    assert reservations == calls == []


def test_upload_rejects_compression_and_client_provider_parameters(web, wav_bytes):
    client, _, reservations, calls = web
    assert client.post(STT, content=wav_bytes(), headers={
        "content-type": "audio/wav", "content-encoding": "gzip",
    }).status_code == 415
    assert client.post(STT + "?model_id=other", content=wav_bytes(),
                       headers={"content-type": "audio/wav"}).status_code == 422
    assert reservations == calls == []


def test_tts_reads_persisted_text_and_returns_uncached_mp3(web):
    client, state, reservations, calls = web
    result = client.post(TTS, headers=HDR)
    assert result.status_code == 200 and result.content == MP3
    assert result.headers["content-type"] == "audio/mpeg"
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-content-type-options"] == "nosniff"
    text = state["messages"][(CONV, MESSAGE)]
    assert json.loads(calls[0].content)["text"] == text
    assert reservations[0][2:] == (CONV, "tts", len(text))


def test_tts_rejects_arbitrary_text_body_and_query(web):
    client, _, reservations, calls = web
    assert client.post(TTS, headers=HDR, json={"text": "Texto arbitrario"}).status_code == 413
    assert client.post(TTS + "?text=arbitrario", headers=HDR).status_code == 422
    assert reservations == calls == []


def test_tts_missing_inbound_or_foreign_message_is_404(web):
    client, state, reservations, calls = web
    state["messages"].clear()
    assert client.post(TTS, headers=HDR).status_code == 404
    assert reservations == calls == []


def test_tts_text_length_is_checked_before_reservation(web):
    client, state, reservations, calls = web
    state["messages"][(CONV, MESSAGE)] = "x" * 2001
    assert client.post(TTS, headers=HDR).status_code == 413
    assert reservations == calls == []


@pytest.mark.parametrize("error,status", [
    (audio.LimitExceeded(60), 429), (audio.BudgetUnavailable(), 503),
])
def test_reservation_failure_prevents_provider_call(web, wav_bytes, error, status):
    client, state, _, calls = web
    state["budget_error"] = error
    result = client.post(STT, content=wav_bytes(), headers={"content-type": "audio/wav"})
    assert result.status_code == status
    if status == 429:
        assert result.headers["retry-after"] == "60"
    assert client.post(TTS, headers=HDR).status_code == status
    assert calls == []


def test_upload_has_a_total_deadline(monkeypatch):
    monkeypatch.setattr(settings, "audio_upload_timeout_seconds", 0.001)

    async def receive():
        await asyncio.sleep(1)
        return {"type": "http.request", "body": b"x", "more_body": False}

    request = Request({"type": "http", "method": "POST", "path": "/", "headers": []}, receive)
    with pytest.raises(HTTPException) as error:
        asyncio.run(audio_routes.read_upload(request, 100))
    assert error.value.status_code == 408
