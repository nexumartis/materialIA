"""Catálogo y precios: producto encontrado, precio fijo, precio vencido, a medida,
producto inexistente (escenarios 1, 3 y 5 del Paso E)."""
from __future__ import annotations

from app.domain import catalog

from conftest import A_KIT_FIXED, A_MAMP_160, A_SELL_EXPIRED, MISSING_ID, TENANT_A


def test_company_a_finds_its_sku():
    found = catalog.search_products(
        TENANT_A, filters={"category": "mampara", "tipo": "corrediza", "color": "negro"}
    )
    skus = {p.sku for p in found}
    assert "MAMP-COR-NEG-160" in skus
    details = catalog.get_product_details(TENANT_A, A_MAMP_160)
    assert details is not None and details.sku == "MAMP-COR-NEG-160"


def test_fixed_price_is_returned():
    price = catalog.get_price(TENANT_A, A_KIT_FIXED)
    assert price.status == "ok"
    assert price.amount == 85000.0 and price.currency == "ARS"


def test_expired_price_is_not_quoted():
    price = catalog.get_price(TENANT_A, A_SELL_EXPIRED)
    assert price.status == "expired"
    assert price.amount is None  # no se afirma un valor vigente


def test_custom_product_requires_human():
    price = catalog.get_price(TENANT_A, A_MAMP_160)
    assert price.status == "requires_human_quote"
    assert price.amount is None


def test_nonexistent_product_is_not_invented():
    price = catalog.get_price(TENANT_A, MISSING_ID)
    assert price.status == "no_price"
    assert catalog.get_product_details(TENANT_A, MISSING_ID) is None
