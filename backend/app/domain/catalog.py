"""Consultas de catálogo y precios. Todas reciben tenant_id resuelto en servidor."""
from __future__ import annotations

from typing import Any, Optional

from ..db import tenant_tx
from ..schemas import PriceResult, ProductSummary


def _row_to_summary(row: dict[str, Any]) -> ProductSummary:
    return ProductSummary(
        id=str(row["id"]),
        sku=row["sku"],
        name=row["name"],
        category=row["category"],
        pricing_mode=row["pricing_mode"],
        specs=row["specs_json"] or {},
        currency=row["currency"],
    )


def search_products(
    tenant_id: str, query: str = "", filters: Optional[dict[str, Any]] = None, limit: int = 10
) -> list[ProductSummary]:
    """Busca productos ACTIVOS de la empresa. Filtros soportados: category, tipo,
    color, material, ancho_mm (tolerancia +-200mm). `query` matchea nombre/sku."""
    filters = filters or {}
    sql = [
        "select id, sku, name, category, pricing_mode, specs_json, currency",
        "from catalog_items",
        "where tenant_id = %(tenant)s and active = true",
    ]
    params: dict[str, Any] = {"tenant": tenant_id}

    if filters.get("category"):
        sql.append("and category = %(category)s")
        params["category"] = filters["category"]
    for spec_key in ("tipo", "color", "material"):
        if filters.get(spec_key):
            sql.append(f"and specs_json->>'{spec_key}' = %({spec_key})s")
            params[spec_key] = str(filters[spec_key])
    if filters.get("ancho_mm"):
        sql.append(
            "and (specs_json->>'ancho_mm') is not null"
            " and abs((specs_json->>'ancho_mm')::int - %(ancho)s) <= 200"
        )
        params["ancho"] = int(filters["ancho_mm"])
    if query:
        sql.append("and (name ilike %(q)s or sku ilike %(q)s)")
        params["q"] = f"%{query}%"

    sql.append("order by name limit %(limit)s")
    params["limit"] = limit

    with tenant_tx(tenant_id) as cur:
        cur.execute("\n".join(sql), params)
        rows = cur.fetchall()
    return [_row_to_summary(r) for r in rows]


def get_product_details(tenant_id: str, product_id: str) -> Optional[ProductSummary]:
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select id, sku, name, category, pricing_mode, specs_json, currency "
            "from catalog_items where tenant_id = %s and id = %s and active = true",
            (tenant_id, product_id),
        )
        row = cur.fetchone()
    return _row_to_summary(row) if row else None


def get_price(tenant_id: str, product_id: str, quantity: int = 1) -> PriceResult:
    """Precio vigente para un producto. No inventa valores:
    - custom_quote  -> requires_human_quote
    - sin precio     -> no_price
    - precio vencido -> expired
    """
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select id, pricing_mode, currency from catalog_items "
            "where tenant_id = %s and id = %s and active = true",
            (tenant_id, product_id),
        )
        item = cur.fetchone()
        if not item:
            return PriceResult(
                product_id=product_id, status="no_price",
                detail="Producto inexistente o inactivo para esta empresa.",
            )
        if item["pricing_mode"] == "custom_quote":
            return PriceResult(
                product_id=product_id, status="requires_human_quote",
                currency=item["currency"],
                detail="Producto a medida: requiere cotización/visita humana.",
            )
        # pricing_mode == fixed -> buscar precio vigente hoy
        cur.execute(
            "select amount, currency, valid_until from price_entries "
            "where tenant_id = %s and item_id = %s "
            "  and valid_from <= current_date "
            "  and (valid_until is null or valid_until >= current_date) "
            "order by valid_from desc limit 1",
            (tenant_id, product_id),
        )
        current = cur.fetchone()
        if current:
            return PriceResult(
                product_id=product_id, status="ok",
                amount=float(current["amount"]) * max(1, quantity),
                currency=current["currency"],
                valid_until=str(current["valid_until"]) if current["valid_until"] else None,
                detail="Precio de lista vigente.",
            )
        # ¿Existe algún precio pero vencido?
        cur.execute(
            "select valid_until from price_entries "
            "where tenant_id = %s and item_id = %s order by valid_until desc nulls last limit 1",
            (tenant_id, product_id),
        )
        any_price = cur.fetchone()
    if any_price:
        return PriceResult(
            product_id=product_id, status="expired",
            detail="El precio de lista está vencido; no se puede afirmar un valor vigente.",
        )
    return PriceResult(
        product_id=product_id, status="no_price",
        detail="No hay precio cargado para este producto.",
    )
