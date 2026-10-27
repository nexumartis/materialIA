"""Tareas de IA en segundo plano (memoria del cliente, resúmenes): una llamada que devuelve JSON.

Corren en el worker, fuera de la respuesta al cliente (sin sumar latencia). Si no hay modelo
configurado o falla, devuelven None y quien llama usa su versión determinista.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

import httpx

from ..config import settings

log = logging.getLogger(__name__)

# (system, user) -> texto JSON. Inyectable en tests.
JsonModel = Callable[[str, str], str]


def _ollama(system: str, user: str) -> str:
    headers = {}
    key = settings.ollama_api_key or settings.llm_api_key
    if key:
        headers["Authorization"] = f"Bearer {key}"
    resp = httpx.post(
        f"{settings.ollama_base_url.rstrip('/')}/api/chat",
        json={"model": settings.ollama_model, "stream": False, "format": "json",
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        headers=headers, timeout=settings.llm_timeout_s,
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content") or ""


def default_model() -> Optional[JsonModel]:
    return _ollama if settings.llm_provider == "ollama" else None


def ask_json(system: str, user: str, model: Optional[JsonModel] = None) -> Optional[dict[str, Any]]:
    model = model or default_model()
    if model is None:
        return None
    try:
        data = json.loads(model(system, user))
    except Exception:  # noqa: BLE001 - modelo caído o JSON inválido: la tarea usa su respaldo
        log.warning("tarea LLM en segundo plano falló", exc_info=True)
        return None
    return data if isinstance(data, dict) else None
