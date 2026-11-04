"""Audio del chat público. No importa main ni acepta texto, URLs, modelos o voces del cliente."""
from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from . import audio, buyer_session
from .config import settings
from .domain import agent_profile, limits, privacy

router = APIRouter(tags=["audio"])
_NO_STORE = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


class AudioCapabilities(BaseModel):
    enabled: bool
    input_mime: str = "audio/wav"
    sample_rate_hz: int = 16000
    channels: int = 1
    sample_width_bits: int = 16
    max_upload_bytes: int
    max_duration_seconds: int
    max_tts_characters: int
    max_transcript_characters: int = audio.MAX_TRANSCRIPT_CHARACTERS


class Transcription(BaseModel):
    text: str = Field(max_length=audio.MAX_TRANSCRIPT_CHARACTERS)
    duration_seconds: float


async def _tenant(slug: str) -> str:
    try:
        store = await run_in_threadpool(agent_profile.tenant_by_slug, slug)
    except Exception:
        raise HTTPException(503, "Audio temporalmente no disponible.") from None
    if store is None:
        raise HTTPException(404, "Tienda no encontrada.")
    return str(store["tenant_id"])


async def _context(slug: str, conversation_id: str | None, token: str | None) -> str:
    tenant = await _tenant(slug)
    if not audio.enabled(tenant):
        raise HTTPException(404, "Audio no disponible para esta tienda.")
    if conversation_id:
        try:
            owned = await run_in_threadpool(buyer_session.owns, tenant, conversation_id, token)
        except Exception:
            raise HTTPException(503, "Audio temporalmente no disponible.") from None
        if not owned:
            raise HTTPException(404, "Conversación no encontrada.")
        try:
            blocked = await run_in_threadpool(privacy.is_blocked, tenant, conversation_id)
        except Exception:
            raise HTTPException(503, "Audio temporalmente no disponible.") from None
        if blocked:
            raise HTTPException(403, "El negocio pausó esta conversación.")
    return tenant


async def read_upload(request: Request, max_bytes: int) -> bytes:
    """El límite se verifica sobre cada chunk, aunque Content-Length mienta o no exista."""
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        raise HTTPException(415, "No se admite un cuerpo comprimido.")
    declared = request.headers.get("content-length")
    if declared is not None:
        if not declared.isdecimal():
            raise HTTPException(400, "Content-Length inválido.")
        try:
            too_large = int(declared) > max_bytes
        except ValueError:
            raise HTTPException(400, "Content-Length inválido.") from None
        if too_large:
            raise HTTPException(413, "El cuerpo supera el tamaño permitido.")
    data = bytearray()
    try:
        async with asyncio.timeout(settings.audio_upload_timeout_seconds):
            async for chunk in request.stream():
                if len(data) + len(chunk) > max_bytes:
                    raise HTTPException(413, "El cuerpo supera el tamaño permitido.")
                data.extend(chunk)
    except TimeoutError:
        raise HTTPException(408, "Se agotó el tiempo para subir el audio.") from None
    except ClientDisconnect:
        raise HTTPException(400, "Se interrumpió la subida del audio.") from None
    return bytes(data)


async def _reserve(request: Request, tenant: str, conversation: str | None, kind: str, units: int) -> None:
    try:
        await run_in_threadpool(audio.reserve, tenant, limits.client_ip(request), conversation, kind, units)
    except audio.LimitExceeded as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": str(exc.window)}) from None
    except audio.BudgetUnavailable:
        raise HTTPException(503, "No podemos reservar cuota de audio en este momento.") from None


def _provider_error(exc: audio.ProviderError) -> HTTPException:
    if isinstance(exc, audio.ProviderTimeout):
        return HTTPException(504, "El proveedor de voz tardó demasiado. La solicitud pudo consumir cuota; no se reintenta automáticamente.")
    return HTTPException(502, "El proveedor de voz no pudo completar la solicitud. No se reintenta automáticamente.")


@router.get("/public/{slug}/audio", response_model=AudioCapabilities)
async def capabilities(slug: str, response: Response) -> AudioCapabilities:
    tenant = await _tenant(slug)
    response.headers.update(_NO_STORE)
    return capabilities_for(tenant)


@router.post("/public/{slug}/audio/transcriptions", response_model=Transcription)
async def transcriptions(
    slug: str, request: Request, response: Response, conversation_id: UUID | None = None,
    token: str | None = Header(None, alias=buyer_session.HEADER),
) -> Transcription:
    conv = str(conversation_id) if conversation_id else None
    tenant = await _context(slug, conv, token)
    if any(key != "conversation_id" for key in request.query_params):
        raise HTTPException(422, "Sólo se admite conversation_id como parámetro.")
    return await transcribe_request(request, response, tenant, conv)


def capabilities_for(tenant: str) -> AudioCapabilities:
    return AudioCapabilities(
        enabled=audio.enabled(tenant), max_upload_bytes=settings.audio_max_upload_bytes,
        max_duration_seconds=settings.audio_max_duration_seconds,
        max_tts_characters=settings.audio_max_tts_characters,
    )


async def transcribe_request(request: Request, response: Response, tenant: str, conv: str | None) -> Transcription:
    """Cuerpo común (tienda y chat de prueba del panel): el llamador ya resolvió tenant y acceso."""
    mime =request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime != "audio/wav":
        raise HTTPException(415, "Enviá el WAV como cuerpo binario con Content-Type: audio/wav.")
    data = await read_upload(request, settings.audio_max_upload_bytes)
    try:
        canonical, duration = await run_in_threadpool(audio.normalize_wav, data)
    except audio.WaveRejected as exc:
        raise HTTPException(415, str(exc)) from None
    await _reserve(request, tenant, conv, "stt", len(canonical))
    try:
        text = await audio.transcribe(canonical)
    except audio.ProviderError as exc:
        raise _provider_error(exc) from None
    response.headers.update(_NO_STORE)
    return Transcription(text=text, duration_seconds=duration)


@router.post(
    "/public/{slug}/conversations/{conversation_id}/messages/{message_id}/audio",
    response_class=Response, responses={200: {"content": {"audio/mpeg": {}}}},
)
async def message_audio(
    slug: str, conversation_id: UUID, message_id: UUID, request: Request,
    token: str | None = Header(None, alias=buyer_session.HEADER),
) -> Response:
    conv = str(conversation_id)
    tenant = await _context(slug, conv, token)
    if request.query_params:
        raise HTTPException(422, "Este endpoint no admite parámetros de consulta.")
    return await speak_request(request, tenant, conv, message_id)


async def speak_request(request: Request, tenant: str, conv: str, message_id: UUID) -> Response:
    """Cuerpo común (tienda y chat de prueba del panel): el llamador ya resolvió tenant y acceso."""
    await read_upload(request, 0)
    try:
        text = await run_in_threadpool(audio.outbound_text, tenant, conv, str(message_id))
    except Exception:
        raise HTTPException(503, "Audio temporalmente no disponible.") from None
    if text is None:
        raise HTTPException(404, "Mensaje no encontrado.")
    if not text.strip():
        raise HTTPException(422, "El mensaje no contiene texto para escuchar.")
    if len(text) > settings.audio_max_tts_characters:
        raise HTTPException(413, "El mensaje supera el límite de texto para escuchar.")
    text = audio.spoken(text)
    await _reserve(request, tenant, conv, "tts", len(text))
    try:
        data = await audio.synthesize(text)
    except audio.ProviderError as exc:
        raise _provider_error(exc) from None
    return Response(data, media_type="audio/mpeg", headers=_NO_STORE)
