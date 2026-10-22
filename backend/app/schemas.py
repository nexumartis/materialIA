"""Contratos tipados (Pydantic) para API y herramientas del agente."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# --- Catálogo -------------------------------------------------------------
class ProductSummary(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    pricing_mode: Literal["fixed", "custom_quote"]
    specs: dict[str, Any] = Field(default_factory=dict)
    currency: str


class PriceResult(BaseModel):
    product_id: str
    status: Literal["ok", "requires_human_quote", "no_price", "expired"]
    amount: Optional[float] = None
    currency: Optional[str] = None
    valid_until: Optional[str] = None
    detail: str = ""


# --- Cotización -----------------------------------------------------------
class QuoteRequirements(BaseModel):
    category: Optional[str] = None
    tipo: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    ancho_mm: Optional[int] = None
    alto_mm: Optional[int] = None
    localidad: Optional[str] = None
    quantity: int = 1
    product_id: Optional[str] = None


class QuoteEstimate(BaseModel):
    requires_human: bool
    status: Literal["estimate", "requires_human_quote", "missing_fields"]
    amount: Optional[float] = None
    currency: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    price_snapshot: Optional[dict[str, Any]] = None
    detail: str = ""


# --- Oportunidades --------------------------------------------------------
class OpportunityInput(BaseModel):
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    stage: str = "nueva"
    origin: str = "web_sandbox"
    requires_human_quote: bool = True
    estimated_amount: Optional[float] = None
    price_snapshot: Optional[dict[str, Any]] = None


class OpportunitySummary(BaseModel):
    id: str
    stage: str
    requires_human_quote: bool
    estimated_amount: Optional[float] = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    created_at: str


# --- API chat -------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    products_referenced: list[ProductSummary] = Field(default_factory=list)
    collected_requirements: dict[str, Any] = Field(default_factory=dict)
    opportunity_id: Optional[str] = None
    conversation_id: str
    missing_fields: list[str] = Field(default_factory=list)
    requires_human: bool = True
    model_used: str
    mode: Literal["mock", "live"]
