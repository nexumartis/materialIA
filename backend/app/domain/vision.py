"""Fotos del cliente → búsqueda en el catálogo.

El cliente manda una foto («tenés esta canilla?», un repuesto roto, una remera). Un modelo con visión
la describe como una BÚSQUEDA corta; esa búsqueda entra al chat como un mensaje normal y el agente
responde con el catálogo real (precio y stock de la base, nunca de la foto).

- **Honestidad:** la foto nunca fija un precio, un stock ni una marca que no se lea en la imagen.
  Si el modelo no reconoce un producto o duda, se le pide al cliente que lo cuente o mande otra.
  Sin modelo de visión configurado, la tienda no ofrece fotos (nunca se finge que se vio).
- **Privacidad:** la imagen no se guarda: se valida, se re-codifica sin metadatos (EXIF, GPS), se
  achica, se describe y se descarta. El modelo tiene la instrucción de ignorar personas y datos.
- **Costo:** cuenta en el tope diario de IA del negocio y tiene límites por IP y por tienda.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any, Callable, Optional

import httpx
from PIL import Image, UnidentifiedImageError

from ..config import settings
from . import ai_usage, limits

log = logging.getLogger(__name__)

FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SIDE = 1024
SYSTEM = (
    "Sos el asistente de un comercio. Te mandan la foto de un producto que el cliente quiere comprar o "
    "reponer. Respondé SOLO un JSON con: es_producto (bool), busqueda (texto corto en castellano para "
    "buscar en un catálogo: tipo de producto, color, material, medida o modelo visibles; máximo 8 palabras), "
    "descripcion (una frase), confianza (\"alta\", \"media\" o \"baja\"). Reglas: no inventes marcas ni "
    "modelos que no se lean en la foto; nunca des precios; ignorá personas, caras, documentos, pantallas y "
    "cualquier dato personal (no los describas). Si la foto no muestra un producto, es_producto=false."
)

# (system, jpeg) -> texto JSON. Inyectable en tests.
Describer = Callable[[str, bytes], str]


class PhotoRejected(ValueError):
    pass


def enabled() -> bool:
    if settings.vision_provider == "ollama":
        return bool(settings.vision_model)
    if settings.vision_provider == "openai":
        return bool(settings.vision_model and settings.llm_api_key)
    return False


def normalize(data: bytes) -> bytes:
    """Valida que sea una imagen real (no por la extensión), la achica y la re-codifica a JPEG sin
    metadatos. Imágenes gigantes (bombas de descompresión) se rechazan."""
    if not data:
        raise PhotoRejected("La foto llegó vacía.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in FORMATS:
                raise PhotoRejected("Mandá la foto en JPG, PNG o WEBP.")
            if img.width * img.height > 40_000_000:
                raise PhotoRejected("La foto es demasiado grande.")
            img = img.convert("RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            out = io.BytesIO()
            img.save(out, "JPEG", quality=85)         # sin exif: no se copia nada de la original
            return out.getvalue()
    except PhotoRejected:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise PhotoRejected("No pude abrir la foto. Probá con otra.") from None


def _ollama(system: str, jpeg: bytes) -> str:
    headers = {}
    key = settings.ollama_api_key or settings.llm_api_key
    if key:
        headers["Authorization"] = f"Bearer {key}"
    resp = httpx.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", headers=headers, timeout=settings.llm_timeout_s,
                      json={"model": settings.vision_model, "stream": False, "format": "json",
                            "options": {"num_predict": 300},
                            "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": "¿Qué producto es?",
                                          "images": [base64.b64encode(jpeg).decode()]}]})
    resp.raise_for_status()
    data = resp.json()
    ai_usage.record(settings.vision_model, data)
    return data.get("message", {}).get("content") or ""


def _openai(system: str, jpeg: bytes) -> str:
    resp = httpx.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions", timeout=settings.llm_timeout_s,
                      headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                      json={"model": settings.vision_model, "max_tokens": 300, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": [
                                             {"type": "text", "text": "¿Qué producto es?"},
                                             {"type": "image_url", "image_url": {
                                                 "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}}]}]})
    resp.raise_for_status()
    data = resp.json()
    ai_usage.record(settings.vision_model, data)
    return data["choices"][0]["message"]["content"] or ""


def _default() -> Optional[Describer]:
    return {"ollama": _ollama, "openai": _openai}.get(settings.vision_provider) if enabled() else None


def _json(text: str) -> dict[str, Any]:
    """Algunos modelos envuelven el JSON en ```json … ```: se toma el primer objeto."""
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start:end + 1]) if start != -1 and end > start else {}
    return data if isinstance(data, dict) else {}


def describe(tenant_id: str, jpeg: bytes, model: Optional[Describer] = None) -> dict[str, Any]:
    """{ok, text, query, description, confidence}. `text` es el mensaje que entra al chat (o None si
    no se reconoció un producto: el cliente recibe `reply` pidiéndole que lo cuente)."""
    model = model or _default()
    if model is None:
        raise PhotoRejected("Esta tienda todavía no recibe fotos.")
    if not limits.ai_allowed(tenant_id):
        raise PhotoRejected("Ahora no puedo mirar fotos. Contame con palabras qué buscás.")
    try:
        with ai_usage.for_tenant(tenant_id, "foto"):
            data = _json(model(SYSTEM, jpeg))
    except Exception:  # noqa: BLE001 - modelo caído o JSON inválido: se pide que lo cuente
        log.warning("no se pudo describir una foto", exc_info=True)
        data = {}
    query = " ".join(str(data.get("busqueda") or "").split())[:80]
    confidence = data.get("confianza") if data.get("confianza") in ("alta", "media", "baja") else "baja"
    description = " ".join(str(data.get("descripcion") or "").split())[:200]
    if not data.get("es_producto") or not query or confidence == "baja":
        return {"ok": False, "text": None, "query": None, "description": description or None, "confidence": confidence,
                "reply": "No llego a distinguir bien el producto en la foto. ¿Me contás qué es, o mandás otra más de cerca?"}
    return {"ok": True, "text": f"Busco esto (te mandé una foto): {query}", "query": query,
            "description": description or None, "confidence": confidence, "reply": None}
