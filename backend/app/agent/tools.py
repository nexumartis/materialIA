"""Contexto de autorización de las herramientas del agente.

El LLM (o el planner) puede proponer QUÉ herramienta llamar y con qué argumentos de negocio,
pero el `tenant_id` sale SIEMPRE de este contexto resuelto por el servidor, nunca de los
argumentos del modelo o del cliente.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ToolContext:
    """Autorización efectiva de la conversación. Inmutable."""
    tenant_id: str
    conversation_id: Optional[str] = None
