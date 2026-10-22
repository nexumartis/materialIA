"""Herramientas del agente: contratos, no magia.

El LLM puede proponer QUÉ herramienta llamar y con qué argumentos de negocio, pero
el `tenant_id` sale SIEMPRE del contexto resuelto por el servidor (ToolContext),
nunca de los argumentos del modelo o del usuario. Si el modelo intenta pasar otro
tenant/producto, la consulta igual filtra por ctx.tenant_id y no devuelve nada.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..domain import catalog, opportunities, pricing
from ..schemas import (
    OpportunityInput,
    OpportunitySummary,
    PriceResult,
    ProductSummary,
    QuoteEstimate,
    QuoteRequirements,
)


@dataclass(frozen=True)
class ToolContext:
    """Autorización efectiva de la conversación. Inmutable."""
    tenant_id: str
    conversation_id: Optional[str] = None


def search_products(ctx: ToolContext, query: str = "", filters: Optional[dict[str, Any]] = None) -> list[ProductSummary]:
    return catalog.search_products(ctx.tenant_id, query=query, filters=filters or {})


def get_product_details(ctx: ToolContext, product_id: str) -> Optional[ProductSummary]:
    return catalog.get_product_details(ctx.tenant_id, product_id)


def get_price(ctx: ToolContext, product_id: str, quantity: int = 1) -> PriceResult:
    return catalog.get_price(ctx.tenant_id, product_id, quantity)


def estimate_quote(ctx: ToolContext, requirements: QuoteRequirements) -> QuoteEstimate:
    return pricing.estimate_quote(ctx.tenant_id, requirements)


def create_or_update_opportunity(ctx: ToolContext, data: OpportunityInput) -> OpportunitySummary:
    # El conversation_id autorizado también se fuerza desde el contexto.
    data = data.model_copy(update={"conversation_id": ctx.conversation_id})
    return opportunities.create_or_update_opportunity(ctx.tenant_id, data)
