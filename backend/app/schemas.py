"""Contratos tipados (Pydantic) para API y herramientas del agente."""
from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import UUID

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


class CatalogItemIn(BaseModel):
    sku: str
    name: str
    category: str
    pricing_mode: Literal["fixed", "custom_quote"] = "custom_quote"
    specs: dict[str, Any] = Field(default_factory=dict)
    currency: str = "ARS"
    active: bool = True


class CatalogImportRequest(BaseModel):
    items: list[CatalogItemIn]


class CatalogImportResult(BaseModel):
    imported: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class PriceResult(BaseModel):
    product_id: str
    status: Literal["ok", "requires_human_quote", "no_price", "expired"]
    amount: Optional[float] = None
    currency: Optional[str] = None
    valid_until: Optional[str] = None
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


class OpportunityUpdate(BaseModel):
    stage: Optional[str] = None
    estimated_amount: Optional[float] = None
    next_action_at: Optional[str] = None


class OpportunitySummary(BaseModel):
    id: str
    stage: str
    requires_human_quote: bool
    estimated_amount: Optional[float] = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    next_action_at: Optional[str] = None


# --- Panel autenticado ----------------------------------------------------
class MeResponse(BaseModel):
    user_id: str
    tenant_id: str
    business_name: str


# --- API chat -------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None




# --- Comprobantes ---------------------------------------------------------
class TransferConfirm(BaseModel):
    """Lo que el dueño cotejó en su banco (la referencia, el importe y la moneda reales)."""
    reference: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    currency: str = Field(default="ARS", min_length=3, max_length=3)
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)


MAX_HUMAN_REPLY = 2000


class HumanReply(BaseModel):
    """Mensaje de una persona del negocio en una conversación de la bandeja."""
    text: str = Field(min_length=1, max_length=MAX_HUMAN_REPLY)
