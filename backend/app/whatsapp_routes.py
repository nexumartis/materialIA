"""Avisos de Meta para WhatsApp. La firma se verifica sobre el cuerpo crudo antes de leer el JSON;
el procesamiento va en segundo plano para contestarle a Meta enseguida.

La ruta no es /webhooks/whatsapp porque POST /webhooks/{provider} es la de los pagos."""
from __future__ import annotations

import hmac
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import whatsapp
from .audio_routes import read_upload
from .config import settings

router = APIRouter(tags=["whatsapp"])
MAX_BODY = 1_000_000


@router.get("/channels/whatsapp/webhook", response_class=PlainTextResponse)
def verify(request: Request) -> str:
    q = request.query_params
    if (whatsapp.enabled() and q.get("hub.mode") == "subscribe"
            and hmac.compare_digest(q.get("hub.verify_token", "").encode(), settings.whatsapp_verify_token.encode())):
        return q.get("hub.challenge", "")
    raise HTTPException(status_code=403, detail="Token de verificación inválido.")


@router.post("/channels/whatsapp/webhook")
async def receive(request: Request, background: BackgroundTasks) -> dict:
    body = await read_upload(request, MAX_BODY)
    if not whatsapp.enabled() or not whatsapp.verify_signature(body, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Firma inválida.")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON inválido.") from None
    if isinstance(payload, dict):
        background.add_task(whatsapp.process_payload, payload)
    return {"ok": True}
