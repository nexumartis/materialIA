"""Aislamiento multiempresa: la empresa D no puede ver ni modificar productos ni
oportunidades de la empresa C, aunque pase IDs reales de C."""
from __future__ import annotations

import pytest

from app.domain import catalog, opportunities
from app.schemas import OpportunityInput

from conftest import C_CANILLA, TENANT_C, TENANT_D


def test_other_company_cannot_read_a_product_by_id():
    assert catalog.get_product_details(TENANT_D, C_CANILLA) is None
    assert catalog.get_price(TENANT_D, C_CANILLA).status == "no_price"


def test_search_returns_only_own_catalog():
    skus = {p.sku for p in catalog.search_products(TENANT_D, query="")}
    assert skus  # D tiene su propio catálogo
    assert not any(s.startswith("GRIF-") for s in skus)  # ningún SKU de C


def test_other_company_cannot_read_an_opportunity():
    opp_c = opportunities.create_or_update_opportunity(
        TENANT_C, OpportunityInput(requirements={"probe": "aislamiento"}, stage="nueva"))
    assert opp_c.id not in {o.id for o in opportunities.list_opportunities(TENANT_D)}
    assert opportunities.get_opportunity(TENANT_D, opp_c.id) is None
    assert opportunities.get_opportunity(TENANT_C, opp_c.id) is not None


def test_other_company_cannot_update_an_opportunity():
    opp = opportunities.create_or_update_opportunity(
        TENANT_C, OpportunityInput(requirements={"x": 1}, stage="nueva"))
    assert opportunities.update_opportunity(TENANT_D, opp.id, stage="cotizada") is None
    assert opportunities.get_opportunity(TENANT_C, opp.id).stage == "nueva"
    updated = opportunities.update_opportunity(
        TENANT_C, opp.id, stage="cotizada", estimated_amount=123000)
    assert updated.stage == "cotizada" and updated.estimated_amount == 123000


def test_update_rejects_invalid_stage():
    opp = opportunities.create_or_update_opportunity(
        TENANT_C, OpportunityInput(requirements={}, stage="nueva"))
    with pytest.raises(ValueError):
        opportunities.update_opportunity(TENANT_C, opp.id, stage="inventado")
