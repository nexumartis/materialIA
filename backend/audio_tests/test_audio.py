import asyncio
import struct
from contextlib import contextmanager

import httpx
import pytest
from pydantic import ValidationError

from app import audio
from app.config import Settings, settings

TENANT = "0000000c-0000-0000-0000-00000000000c"
MP3 = b"\xff\xfb\x90\x64" + b"\0" * 128


@pytest.mark.parametrize("name,value", [
    ("audio_demo_enabled", False), ("audio_api_key", ""),
    ("audio_api_key", "bad\nkey"), ("audio_voice_id", ""),
    ("audio_voice_id", "../voice"), ("audio_tts_model", ""),
    ("audio_demo_tenant", ""),
    ("audio_demo_tenant", "0000000a-0000-0000-0000-00000000000a"),
    ("audio_daily_calls_global", 0), ("audio_provider_timeout_seconds", float("inf")),
])
def test_incomplete_or_invalid_configuration_disables_audio(monkeypatch, name, value):
    assert audio.enabled(TENANT)
    monkeypatch.setattr(settings, name, value)
    assert not audio.enabled(TENANT)


def test_configuration_defaults_are_off(audio_config):
    values = {**audio_config, "audio_demo_enabled": False, "audio_api_key": "",
              "audio_voice_id": "", "audio_demo_tenant": ""}
    default = Settings(_env_file=None, **values)
    assert default.audio_demo_enabled is False
    assert not audio.enabled("0000000d-0000-0000-0000-00000000000d")


@pytest.mark.parametrize("name", audio.POSITIVE_SETTINGS)
def test_audio_limits_cannot_be_disabled_with_zero(audio_config, name):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**audio_config, name: 0})


def test_wav_duration_is_verified_and_extra_chunks_are_removed(wav_bytes):
    original = wav_bytes()
    extra = b"JUNK" + struct.pack("<I", 6) + b"secret"
    source = bytearray(original + extra)
    struct.pack_into("<I", source, 4, len(source) - 8)
    canonical, duration = audio.normalize_wav(bytes(source))
    assert canonical == original
    assert duration == 0.1
    assert b"secret" not in canonical


@pytest.mark.parametrize("options", [
    {"seconds": 0}, {"seconds": 31}, {"channels": 2},
    {"rate": 8000}, {"width": 3},
])
def test_wav_rejects_unbounded_duration_or_unsupported_pcm(wav_bytes, options):
    with pytest.raises(audio.WaveRejected):
        audio.normalize_wav(wav_bytes(**options))


def test_wav_rejects_false_sizes_and_magic(wav_bytes):
    good = wav_bytes()
    false_data_size = bytearray(good)
    struct.pack_into("<I", false_data_size, 40, 16000)
    for data in (b"not audio", good[:-1], bytes(false_data_size), b"RF64" + good[4:]):
        with pytest.raises(audio.WaveRejected):
            audio.normalize_wav(data)


def test_stt_uses_fixed_official_endpoint_multipart_and_backend_model(provider, wav_bytes):
    calls, respond = provider
    respond(lambda request: httpx.Response(200, json={"text": "Canilla sintética"}))
    assert asyncio.run(audio.transcribe(wav_bytes())) == "Canilla sintética"
    request = calls[0]
    assert str(request.url) == "https://api.elevenlabs.io/v1/speech-to-text"
    assert request.headers["xi-api-key"] == "synthetic-key"
    assert request.headers["accept-encoding"] == "identity"
    assert "multipart/form-data" in request.headers["content-type"]
    assert b'name="model_id"' in request.content and b"scribe_v2" in request.content
    assert b'filename="audio.wav"' in request.content and b"RIFF" in request.content
    assert b"enable_logging" not in request.content


def test_tts_only_uses_backend_voice_model_and_fixed_output_format(provider):
    import json
    calls, respond = provider
    respond(lambda request: httpx.Response(200, content=MP3, headers={"content-type": "audio/mpeg"}))
    assert asyncio.run(audio.synthesize("Respuesta sintética")) == MP3
    request = calls[0]
    assert request.url.host == "api.elevenlabs.io"
    assert request.url.path == "/v1/text-to-speech/synthetic-voice"
    assert request.url.params.multi_items() == [("output_format", "mp3_44100_128")]
    assert json.loads(request.content) == {
        "text": "Respuesta sintética", "model_id": "eleven_multilingual_v2",
    }


@pytest.mark.parametrize("response", [
    httpx.Response(401, text="external-secret"),
    httpx.Response(302, headers={"location": "http://127.0.0.1/private"}),
    httpx.Response(200, content=b"{}", headers={"content-type": "text/html"}),
    httpx.Response(200, json={"text": ["external-secret"]}),
    httpx.Response(200, json={"text": "x" * 2001}),
    httpx.Response(200, content=b"{" * 100, headers={"content-type": "application/json"}),
    httpx.Response(200, content=b"x" * 65537, headers={"content-type": "application/json"}),
    httpx.Response(200, content=b"{}", headers={
        "content-type": "application/json", "content-encoding": "br",
    }),
])
def test_external_stt_responses_are_bounded_validated_and_never_exposed(provider, wav_bytes, response):
    calls, respond = provider
    respond(lambda request: response)
    with pytest.raises(audio.ProviderError) as error:
        asyncio.run(audio.transcribe(wav_bytes()))
    assert "external-secret" not in str(error.value)
    assert len(calls) == 1


class Chunks(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield MP3
        yield b"x" * 100


def test_tts_stream_without_content_length_is_bounded(provider, monkeypatch):
    calls, respond = provider
    monkeypatch.setattr(settings, "audio_max_response_bytes", len(MP3))
    respond(lambda request: httpx.Response(200, stream=Chunks(), headers={"content-type": "audio/mpeg"}))
    with pytest.raises(audio.ProviderError):
        asyncio.run(audio.synthesize("Sintético"))
    assert len(calls) == 1


@pytest.mark.parametrize("mime,body", [
    ("text/html", MP3), ("audio/mpeg", b"not mp3"),
    ("audio/mpeg", b"ID3\x04\0\0\0\0\0\0"),
])
def test_tts_checks_external_mime_and_magic(provider, mime, body):
    _, respond = provider
    respond(lambda request: httpx.Response(200, content=body, headers={"content-type": mime}))
    with pytest.raises(audio.ProviderError):
        asyncio.run(audio.synthesize("Sintético"))


def test_provider_timeout_has_no_retry_or_sensitive_error(provider, wav_bytes):
    calls, respond = provider

    def timeout(request):
        raise httpx.ReadTimeout("external-secret synthetic-key")

    respond(timeout)
    with pytest.raises(audio.ProviderTimeout) as error:
        asyncio.run(audio.transcribe(wav_bytes()))
    assert "synthetic-key" not in str(error.value)
    assert len(calls) == 1


def test_total_provider_deadline_bounds_a_slow_response(provider, monkeypatch, wav_bytes):
    calls, respond = provider
    monkeypatch.setattr(settings, "audio_provider_timeout_seconds", 0.001)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json={"text": "Sintético"})

    respond(slow)
    with pytest.raises(audio.ProviderTimeout):
        asyncio.run(audio.transcribe(wav_bytes()))
    assert len(calls) == 1


def test_disabled_provider_never_opens_http(provider, monkeypatch, wav_bytes):
    calls, _ = provider
    monkeypatch.setattr(settings, "audio_api_key", "")
    with pytest.raises(audio.ProviderError):
        asyncio.run(audio.transcribe(wav_bytes()))
    assert calls == []


def test_budget_database_failure_is_closed_and_sanitized(monkeypatch):
    @contextmanager
    def unavailable():
        raise RuntimeError("database-secret")
        yield

    monkeypatch.setattr(audio, "system_tx", unavailable)
    with pytest.raises(audio.BudgetUnavailable) as error:
        audio.reserve(TENANT, "synthetic-ip", None, "stt", 100)
    assert "database-secret" not in str(error.value)


def test_spoken_summarizes_numbered_list_and_says_pesos():
    text = ("Tenés estas:\n\n"
            "1. Canilla cromo — Hidrolar (DEMO) · $68.000 · 10 unidades  \n"
            "2. Canilla negra — Aquaflux (DEMO) · $74.500 · última unidad  \n\n"
            "¿Te sirve alguna?")
    said = audio.spoken(text)
    assert said == ("Tenés estas:\n\nTe dejé 2 opciones acá abajo. La primera es Canilla cromo, "
                    "a 68.000 pesos.\n\n¿Te sirve alguna?")
    assert audio.spoken("Total: $68.000") == "Total: 68.000 pesos"
    assert audio.spoken("Hola") == "Hola"
