"""Pruebas pequeñas: sin DB, proveedor HTTP siempre simulado."""
import inspect
import io
import wave

import httpx
import pytest

from app import audio
from app.config import settings


@pytest.fixture(autouse=True)
def audio_config(monkeypatch):
    values = {
        "audio_demo_enabled": True,
        "audio_demo_tenant": "0000000c-0000-0000-0000-00000000000c",
        "audio_api_key": "synthetic-key",
        "audio_voice_id": "synthetic-voice",
        "audio_tts_model": "eleven_multilingual_v2",
        "audio_max_upload_bytes": 1_000_000,
        "audio_max_duration_seconds": 30,
        "audio_max_tts_characters": 2000,
        "audio_max_response_bytes": 1_000_000,
        "audio_upload_timeout_seconds": 10.0,
        "audio_provider_timeout_seconds": 20.0,
        "audio_ip_per_minute": 3,
        "audio_conversation_per_hour": 10,
        "audio_daily_calls_per_tenant": 100,
        "audio_daily_calls_global": 200,
        "audio_daily_stt_bytes_per_tenant": 30_000_000,
        "audio_daily_stt_bytes_global": 60_000_000,
        "audio_daily_tts_characters_per_tenant": 20_000,
        "audio_daily_tts_characters_global": 40_000,
    }
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)
    return values


@pytest.fixture
def wav_bytes():
    def make(seconds=0.1, channels=1, rate=16000, width=2):
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(channels)
            wav.setframerate(rate)
            wav.setsampwidth(width)
            wav.writeframes(b"\0" * (int(seconds * rate) * channels * width))
        return output.getvalue()
    return make


@pytest.fixture(autouse=True)
def provider(monkeypatch):
    calls = []

    def unexpected(request):
        pytest.fail("Solicitud de proveedor no prevista por la prueba")

    responder = unexpected

    def respond(handler):
        nonlocal responder
        responder = handler

    async def handle(request):
        await request.aread()
        calls.append(request)
        result = responder(request)
        return await result if inspect.isawaitable(result) else result

    monkeypatch.setattr(audio, "provider_client", lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handle), trust_env=False,
    ))
    return calls, respond
