"""Audio efímero, proveedor fijo y reservas compartidas que fallan cerrado.

No guarda originales, transcripciones ni respuestas de voz; tampoco registra cuerpos o secretos.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import re
import struct
import wave

import httpx

from .config import settings
from .db import system_tx, tenant_tx

DEMO_TENANTS = frozenset({
    "0000000c-0000-0000-0000-00000000000c",
    "0000000d-0000-0000-0000-00000000000d",
})
MAX_TRANSCRIPT_CHARACTERS = 2000
MAX_STT_RESPONSE_BYTES = 65536
BUCKET_PREFIX = "audio-v1"
_IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_KEY = re.compile(r"[A-Za-z0-9_-]{1,512}\Z")
POSITIVE_SETTINGS = (
    "audio_max_upload_bytes", "audio_max_duration_seconds", "audio_max_tts_characters",
    "audio_max_response_bytes", "audio_upload_timeout_seconds", "audio_provider_timeout_seconds",
    "audio_ip_per_minute", "audio_conversation_per_hour", "audio_daily_calls_per_tenant",
    "audio_daily_calls_global", "audio_daily_stt_bytes_per_tenant", "audio_daily_stt_bytes_global",
    "audio_daily_tts_characters_per_tenant", "audio_daily_tts_characters_global",
)


def enabled(tenant_id: str) -> bool:
    return bool(
        settings.audio_demo_enabled
        and settings.audio_demo_tenant in DEMO_TENANTS
        and str(tenant_id) == settings.audio_demo_tenant
        and _KEY.fullmatch(settings.audio_api_key)
        and _IDENTIFIER.fullmatch(settings.audio_voice_id)
        and _IDENTIFIER.fullmatch(settings.audio_tts_model)
        and all(math.isfinite(getattr(settings, name)) and getattr(settings, name) > 0
                for name in POSITIVE_SETTINGS)
    )


class WaveRejected(ValueError):
    def __init__(self):
        super().__init__("Usá un WAV PCM mono de 16 kHz y 16 bits dentro de la duración permitida.")


class ProviderError(RuntimeError):
    def __init__(self):
        super().__init__("El proveedor de voz no pudo completar la solicitud.")


class ProviderTimeout(ProviderError):
    pass


class BudgetUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("Audio temporalmente no disponible.")


class LimitExceeded(RuntimeError):
    def __init__(self, window: int):
        super().__init__("Se alcanzó un límite de audio. Esperá antes de volver a intentarlo.")
        self.window = window


def normalize_wav(data: bytes) -> tuple[bytes, float]:
    """Verifica frames reales y reconstruye sólo ese PCM: sin metadatos ni chunks ocultos."""
    try:
        if (len(data) < 44 or len(data) > settings.audio_max_upload_bytes
                or data[:4] != b"RIFF" or data[8:12] != b"WAVE"
                or struct.unpack_from("<I", data, 4)[0] != len(data) - 8):
            raise WaveRejected()
        with wave.open(io.BytesIO(data), "rb") as source:
            frames = source.getnframes()
            if (source.getcomptype() != "NONE" or source.getnchannels() != 1
                    or source.getsampwidth() != 2 or source.getframerate() != 16000
                    or not 0 < frames <= 16000 * settings.audio_max_duration_seconds):
                raise WaveRejected()
            pcm = source.readframes(frames + 1)
            if len(pcm) != frames * 2:
                raise WaveRejected()
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(16000)
            target.writeframes(pcm)
        canonical = output.getvalue()
        if len(canonical) > settings.audio_max_upload_bytes:
            raise WaveRejected()
        return canonical, frames / 16000
    except (wave.Error, EOFError, struct.error):
        raise WaveRejected() from None


def _bucket(scope: str, key: str) -> str:
    digest = hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()
    return f"{BUCKET_PREFIX}:{scope}:{digest}"


def reserve(tenant_id: str, ip: str, conversation_id: str | None, kind: str, units: int) -> None:
    """Reserva TODO en una transacción antes del proveedor. No hay devolución ni reintento.

    El UPSERT condicional serializa cada cubo; una excepción revierte todos los anteriores.
    Orden global estable para evitar deadlocks entre solicitudes de tenants distintos.
    """
    if kind not in ("stt", "tts") or not 0 < units <= 2_000_000_000:
        raise BudgetUnavailable()
    checks = [
        ("ip", ip, settings.audio_ip_per_minute, 60, 1),
        ("tenant-calls", tenant_id, settings.audio_daily_calls_per_tenant, 86400, 1),
        ("global-calls", "all", settings.audio_daily_calls_global, 86400, 1),
    ]
    if conversation_id:
        checks.append(("conversation", f"{tenant_id}:{conversation_id}",
                       settings.audio_conversation_per_hour, 3600, 1))
    if kind == "stt":
        checks.extend([
            ("tenant-stt-bytes", tenant_id, settings.audio_daily_stt_bytes_per_tenant, 86400, units),
            ("global-stt-bytes", "all", settings.audio_daily_stt_bytes_global, 86400, units),
        ])
    else:
        checks.extend([
            ("tenant-tts-characters", tenant_id, settings.audio_daily_tts_characters_per_tenant, 86400, units),
            ("global-tts-characters", "all", settings.audio_daily_tts_characters_global, 86400, units),
        ])
    if any(not 0 < limit <= 2_000_000_000 for _, _, limit, _, _ in checks):
        raise BudgetUnavailable()
    for _, _, limit, window, weight in checks:
        if weight > limit:
            raise LimitExceeded(window)
    rows = sorted((_bucket(scope, key), limit, window, weight)
                  for scope, key, limit, window, weight in checks)
    try:
        with system_tx() as cur:
            cur.execute("set local statement_timeout = '3000ms'")
            cur.execute("set local lock_timeout = '2000ms'")
            for bucket, limit, window, weight in rows:
                cur.execute(
                    "insert into rate_limits (bucket, window_start, hits) values "
                    "(%s, to_timestamp(floor(extract(epoch from now()) / %s) * %s), %s) "
                    "on conflict (bucket, window_start) do update "
                    "set hits = rate_limits.hits + excluded.hits "
                    "where rate_limits.hits <= %s - excluded.hits returning hits",
                    (bucket, window, window, weight, limit),
                )
                if cur.fetchone() is None:
                    raise LimitExceeded(window)
    except LimitExceeded:
        raise
    except Exception:
        # Sin detalles de DB, IP, token ni cuerpos en logs o en respuestas.
        raise BudgetUnavailable() from None


def outbound_text(tenant_id: str, conversation_id: str, message_id: str) -> str | None:
    """Frontera de persistencia; el llamador ya acreditó posesión de la conversación."""
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select left(content, %s) as content from messages "
            "where tenant_id = %s and conversation_id = %s and id = %s and direction = 'outbound'",
            (settings.audio_max_tts_characters + 1, tenant_id, conversation_id, message_id),
        )
        row = cur.fetchone()
    return row["content"] if row else None


_ITEM = re.compile(r"^\s*\d+\.\s+")
_PESOS = re.compile(r"\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d+)?)")


def spoken(text: str) -> str:
    """Versión para escuchar: la lista numerada ya está en las tarjetas, así que en voz se
    resume (cuántas opciones y la primera con su precio real) y `$` se dice «pesos»."""
    lines = text.splitlines()
    out, items = [], [line for line in lines if _ITEM.match(line)]
    for line in lines:
        if not _ITEM.match(line):
            out.append(line)
        elif line is items[0]:
            first = _ITEM.sub("", line)
            price = _PESOS.search(first)
            name = first.split(" — ")[0].strip()
            out.append((f"Te dejé {len(items)} opciones acá abajo. La primera es {name}"
                        if len(items) > 1 else f"Te la dejé acá abajo: {name}")
                       + (f", a {price.group(0)}." if price else "."))
    said = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return _PESOS.sub(r"\1 pesos", said)


def provider_client() -> httpx.AsyncClient:
    """Frontera HTTP reemplazable por MockTransport; sin proxies del entorno ni redirects."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.audio_provider_timeout_seconds),
        follow_redirects=False, trust_env=False,
    )


async def _post(path: str, mime: str, max_bytes: int, **kwargs) -> bytes:
    if not enabled(settings.audio_demo_tenant):
        raise ProviderError()
    try:
        async with asyncio.timeout(settings.audio_provider_timeout_seconds):
            async with provider_client() as client:
                async with client.stream(
                    "POST", "https://api.elevenlabs.io/v1/" + path,
                    headers={"xi-api-key": settings.audio_api_key,
                             "Accept": mime, "Accept-Encoding": "identity"},
                    **kwargs,
                ) as response:
                    if (response.status_code != 200
                            or response.headers.get("content-type", "").split(";", 1)[0].strip().lower() != mime
                            or response.headers.get("content-encoding", "identity").lower() != "identity"):
                        raise ProviderError()
                    declared = response.headers.get("content-length")
                    if declared is not None and (not declared.isdecimal() or int(declared) > max_bytes):
                        raise ProviderError()
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=16384):
                        if len(body) + len(chunk) > max_bytes:
                            raise ProviderError()
                        body.extend(chunk)
                    return bytes(body)
    except (httpx.TimeoutException, TimeoutError):
        raise ProviderTimeout() from None
    except (httpx.RequestError, ValueError):
        raise ProviderError() from None


async def transcribe(data: bytes) -> str:
    body = await _post(
        "speech-to-text", "application/json", MAX_STT_RESPONSE_BYTES,
        data={"model_id": "scribe_v2"}, files={"file": ("audio.wav", data, "audio/wav")},
    )
    try:
        result = json.loads(body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise ProviderError() from None
    if (not isinstance(result, dict) or not isinstance(result.get("text"), str)
            or len(result["text"]) > MAX_TRANSCRIPT_CHARACTERS):
        raise ProviderError()
    return result["text"].strip()


def _mp3(data: bytes) -> bool:
    offset = 0
    if data.startswith(b"ID3"):
        if len(data) < 10 or data[3] not in (2, 3, 4) or any(value & 128 for value in data[6:10]):
            return False
        size = 0
        for value in data[6:10]:
            size = (size << 7) | value
        offset = 10 + size
        if data[3] == 4 and data[5] & 16:
            offset += 10
    frame = data[offset:offset + 4]
    return bool(len(frame) == 4 and frame[0] == 255 and frame[1] & 224 == 224
                and (frame[1] >> 3) & 3 != 1 and (frame[1] >> 1) & 3 == 1
                and (frame[2] >> 4) not in (0, 15) and (frame[2] >> 2) & 3 != 3)


async def synthesize(text: str) -> bytes:
    if not text.strip() or len(text) > settings.audio_max_tts_characters:
        raise ProviderError()
    body = await _post(
        f"text-to-speech/{settings.audio_voice_id}", "audio/mpeg", settings.audio_max_response_bytes,
        params={"output_format": "mp3_44100_128"},
        json={"text": text, "model_id": settings.audio_tts_model},
    )
    if not _mp3(body):
        raise ProviderError()
    return body
