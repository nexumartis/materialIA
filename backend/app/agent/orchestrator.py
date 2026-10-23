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
from .llm_adapter import _CLOSING, get_provider

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

    history = opportunities.get_recent_messages(tenant_id, conversation_id)
    understanding = provider.understand(message, history=history)

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

    # --- Saludo/cierre sin pedido: respuesta breve, sin re-registrar la oportunidad ---
    new_preview = {k: v for k, v in understanding.requirements.items() if v is not None}
    if not new_preview and not understanding.customer_name and _CLOSING.search(message):
        reply = provider.compose_reply({"company_name": company, "closing": True})
        opportunities.add_message(tenant_id, conversation_id, "outbound", reply)
        opportunities.audit(tenant_id, "closing", conversation_id,
                            {"mode": understanding.mode, "model": understanding.model_used})
        return ChatResponse(
            reply=reply, products_referenced=[], collected_requirements={},
            opportunity_id=None, conversation_id=conversation_id, missing_fields=[],
            requires_human=False, model_used=understanding.model_used, mode=understanding.mode,
        )

    # --- Memoria del chat: acumular requisitos de turnos previos de esta conversación ---
    prior = opportunities.get_conversation_requirements(tenant_id, conversation_id)
    new_req = {k: v for k, v in understanding.requirements.items() if v is not None}
    merged = {**prior, **new_req}
    if understanding.customer_name:
        merged["customer_name"] = understanding.customer_name

    # El catálogo se matchea por categoría/tipo para decidir si se trabaja ese producto.
    # Color, material y medida son datos de cotización (producto a medida), NO filtros de
    # existencia: evita el falso "no trabajamos" por un color o una medida fuera de lista.
    filters = {k: merged[k] for k in ("category", "tipo") if merged.get(k)}
    products = tools.search_products(ctx, query="", filters=filters) if filters else []

    quote_req = QuoteRequirements(**{k: v for k, v in merged.items() if k in _QUOTE_FIELDS})
    estimate = tools.estimate_quote(ctx, quote_req)

    # Hay intención de cotizar si en ALGÚN turno se nombró producto/tipo.
    asked_for_product = bool(merged.get("category") or merged.get("tipo")) or understanding.intent == "quote_request"
    no_match = asked_for_product and bool(filters) and not products

    # --- Construir la decisión de negocio para la redacción ---
    decision: dict[str, Any] = {
        "company_name": company,
        "adversarial": False,
        "no_match": no_match,
        "requires_human": estimate.requires_human,
        "missing_fields": estimate.missing_fields,
        "producto": merged.get("category"),
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
    collected = merged

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
