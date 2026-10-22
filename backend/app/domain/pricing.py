"""Cotizador determinista. No hay fórmula de negocio validada para mamparas a
medida, así que NO inventa importes: devuelve requires_human con los datos que faltan.
Sólo los SKU de precio fijo con precio vigente producen un importe computable.
"""
from __future__ import annotations

from typing import Optional

from . import catalog
from ..schemas import QuoteEstimate, QuoteRequirements

# Datos mínimos para preparar una solicitud de cotización de mampara a medida.
REQUIRED_FOR_CUSTOM = ["tipo", "color", "ancho_mm", "alto_mm", "localidad"]


def estimate_quote(tenant_id: str, req: QuoteRequirements) -> QuoteEstimate:
    # Caso 1: producto puntual de precio fijo (accesorio con lista vigente).
    if req.product_id:
        price = catalog.get_price(tenant_id, req.product_id, req.quantity)
        if price.status == "ok":
            return QuoteEstimate(
                requires_human=False, status="estimate",
                amount=price.amount, currency=price.currency,
                price_snapshot={
                    "product_id": req.product_id, "quantity": req.quantity,
                    "unit_currency": price.currency, "valid_until": price.valid_until,
                    "amount": price.amount,
                },
                detail="Importe de lista vigente (sin cálculo técnico a medida).",
            )
        if price.status in ("requires_human_quote", "expired", "no_price"):
            return QuoteEstimate(
                requires_human=True, status="requires_human_quote",
                detail=price.detail,
            )

    # Caso 2: mampara/abertura a medida -> faltantes + cotización humana.
    missing = _missing_fields(req)
    if missing:
        return QuoteEstimate(
            requires_human=True, status="missing_fields", missing_fields=missing,
            detail="Faltan datos para preparar la solicitud de cotización.",
        )
    return QuoteEstimate(
        requires_human=True, status="requires_human_quote",
        detail="Datos completos: se deriva a una persona para cotizar (producto a medida).",
    )


def _missing_fields(req: QuoteRequirements) -> list[str]:
    values = {
        "tipo": req.tipo, "color": req.color, "ancho_mm": req.ancho_mm,
        "alto_mm": req.alto_mm, "localidad": req.localidad,
    }
    return [k for k in REQUIRED_FOR_CUSTOM if not values.get(k)]
