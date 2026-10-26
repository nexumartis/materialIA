"""Catálogo y precios: producto encontrado, precio fijo, precio vencido, a medida,
producto inexistente. Nunca se inventa un precio."""
from __future__ import annotations

from app.domain import catalog

from conftest import D_CUSTOM, D_EXPIRED, D_FIXED, MISSING_ID, TENANT_D


def test_company_finds_its_sku():
    found = catalog.search_products(TENANT_D, query="martillo")
    assert "FER-MART-500" in {p.sku for p in found}
    details = catalog.get_product_details(TENANT_D, D_FIXED)
    assert details is not None and details.sku == "FER-MART-500"


def test_fixed_price_is_returned():
    price = catalog.get_price(TENANT_D, D_FIXED)
    assert price.status == "ok"
    assert price.amount == 18500.0 and price.currency == "ARS"


def test_expired_price_is_not_quoted():
    price = catalog.get_price(TENANT_D, D_EXPIRED)
    assert price.status == "expired"
    assert price.amount is None  # no se afirma un valor vigente


def test_custom_product_requires_human():
    price = catalog.get_price(TENANT_D, D_CUSTOM)
    assert price.status == "requires_human_quote"
    assert price.amount is None


def test_catalog_import_adds_and_validates():
    n, errs = catalog.import_items(TENANT_D, [
        {"sku": "TEST-IMP-1", "name": "Pinza test importada", "category": "herramientas",
         "pricing_mode": "fixed", "specs": {"largo": "20 cm"}},
    ])
    assert n == 1 and not errs
    found = catalog.search_products(TENANT_D, query="TEST-IMP-1")
    assert any(p.sku == "TEST-IMP-1" for p in found)
    # pricing_mode inválido -> error, no se inserta
    n2, errs2 = catalog.import_items(TENANT_D, [
        {"sku": "TEST-IMP-BAD", "name": "x", "category": "herramientas", "pricing_mode": "raro"}])
    assert n2 == 0 and errs2


def test_nonexistent_product_is_not_invented():
    price = catalog.get_price(TENANT_D, MISSING_ID)
    assert price.status == "no_price"
    assert catalog.get_product_details(TENANT_D, MISSING_ID) is None
