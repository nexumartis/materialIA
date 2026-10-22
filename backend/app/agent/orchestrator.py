"""Orquestador de conversación.

El LLM (o el mock) interpreta y redacta; el BACKEND decide y ejecuta las herramientas,
persiste y audita. Nunca se inventan precios ni stock; el aislamiento por empresa lo
garantiza ToolContext (tenant resuelto en servidor).
"""
from __future__ import annotations

from typing import Any, Optional

from ..db import tenant_tx
from ..domain import opportunities
from ..schemas import ChatResponse, OpportunityInput, QuoteRequirements
from . import tools
from .llm_adapter import get_provider

_QUOTE_FIELDS = {"category", "tipo", "color", "material", "ancho_mm", "alto_mm", "localidad", "product_id", "quantity"}


def _tenant_name(tenant_id: str) -> str:
    with tenant_tx(tenant_id) as cur:
        cur.execute("select name from tenants where id = %s", (tenant_id,))
        row = cur.fetchone()
    return row["name"] if row else "el negocio"


def handle_chat(tenant_id: str, message: str, conversation_id: Optional[str] = None) -> ChatResponse:
    provider = get_provider()
    conversation_id = opportunities.ensure_conversation(tenant_id, conversation_id)
    opportunities.add_message(tenant_id, conversation_id, "inbound", message)
    ctx = tools.ToolContext(tenant_id=tenant_id, conversation_id=conversation_id)
    company = _tenant_name(tenant_id)

    understanding = provider.understand(message, history=[])

    # --- Mensaje adversarial: denegar sin filtrar nada de otra empresa ---
    if understanding.adversarial:
        reply = provider.compose_reply({"adversarial": True, "company_name": company})
        opportunities.add_message(tenant_id, conversation_id, "outbound", reply)
        opportunities.audit(tenant_id, "adversarial_denied", conversation_id,
                            {"mode": understanding.mode, "model": understanding.model_used})
        return ChatResponse(
            reply=reply, products_referenced=[], collected_requirements={},
            opportunity_id=None, conversation_id=conversation_id, missing_fields=[],
            requires_human=True, model_used=understanding.model_used, mode=understanding.mode,
        )

    req = understanding.requirements
    filters = {k: req[k] for k in ("category", "tipo", "color", "material", "ancho_mm") if req.get(k)}
    products = tools.search_products(ctx, query="", filters=filters) if filters else []

    quote_req = QuoteRequirements(**{k: v for k, v in req.items() if k in _QUOTE_FIELDS})
    estimate = tools.estimate_quote(ctx, quote_req)

    asked_for_product = understanding.intent == "quote_request"
    no_match = asked_for_product and bool(filters) and not products

    # --- Construir la decisión de negocio para la redacción ---
    decision: dict[str, Any] = {
        "company_name": company,
        "adversarial": False,
        "no_match": no_match,
        "requires_human": estimate.requires_human,
        "missing_fields": estimate.missing_fields,
        "trabajamos_text": "Sí, trabajamos ese tipo de productos. " if products else "",
    }
    if estimate.status == "estimate" and estimate.amount is not None:
        decision["price_text"] = (
            f"Según lista vigente son {estimate.amount:,.2f} {estimate.currency}. "
            "Lo confirma un asesor antes de cerrar."
        )
    reply = provider.compose_reply(decision)

    # --- Persistir oportunidad (si hubo intención de cotizar) ---
    opportunity_id: Optional[str] = None
    collected = dict(req)
    if understanding.customer_name:
        collected["customer_name"] = understanding.customer_name

    if asked_for_product:
        if estimate.status == "missing_fields":
            stage = "datos_incompletos"
        elif estimate.status == "estimate":
            stage = "cotizada"
        else:
            stage = "para_cotizar"
        opp = tools.create_or_update_opportunity(ctx, OpportunityInput(
            requirements=collected, stage=stage, origin="web_sandbox",
            requires_human_quote=estimate.requires_human,
            estimated_amount=estimate.amount, price_snapshot=estimate.price_snapshot,
        ))
        opportunity_id = opp.id

    opportunities.add_message(tenant_id, conversation_id, "outbound", reply)
    opportunities.audit(tenant_id, "chat_handled", opportunity_id, {
        "mode": understanding.mode, "model": understanding.model_used,
        "intent": understanding.intent, "products_count": len(products),
        "missing_fields": estimate.missing_fields, "requires_human": estimate.requires_human,
        "no_match": no_match,
    })

    return ChatResponse(
        reply=reply, products_referenced=products[:5], collected_requirements=collected,
        opportunity_id=opportunity_id, conversation_id=conversation_id,
        missing_fields=estimate.missing_fields, requires_human=estimate.requires_human,
        model_used=understanding.model_used, mode=understanding.mode,
    )
