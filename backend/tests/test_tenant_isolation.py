"""Aislamiento multiempresa (escenarios 1 y 2 del Paso E): la Empresa B no puede ver
ni modificar productos ni oportunidades de la Empresa A, aunque pase IDs de A."""
from __future__ import annotations

import pytest

from app.domain import catalog, opportunities
from app.schemas import OpportunityInput

from conftest import A_MAMP_160, TENANT_A, TENANT_B


def test_b_cannot_read_a_product_by_id():
    # B intenta leer un producto de A pasando el ID real de A.
    assert catalog.get_product_details(TENANT_B, A_MAMP_160) is None
    price = catalog.get_price(TENANT_B, A_MAMP_160)
    assert price.status == "no_price"  # para B ese producto no existe


def test_search_returns_only_own_catalog():
    b_items = catalog.search_products(TENANT_B, query="")
    skus = {p.sku for p in b_items}
    assert skus  # B tiene su propio catálogo
    assert not any(s.startswith("MAMP-COR-NEG") for s in skus)  # ningún SKU de A


def test_b_cannot_read_a_opportunity():
    opp_a = opportunities.create_or_update_opportunity(
        TENANT_A, OpportunityInput(requirements={"probe": "aislamiento"}, stage="nueva")
    )
    # B no la ve en su listado ni la puede leer por ID.
    b_ids = {o.id for o in opportunities.list_opportunities(TENANT_B)}
    assert opp_a.id not in b_ids
    assert opportunities.get_opportunity(TENANT_B, opp_a.id) is None
    # A sí la ve.
    assert opportunities.get_opportunity(TENANT_A, opp_a.id) is not None


def test_b_cannot_update_a_opportunity():
    opp = opportunities.create_or_update_opportunity(
        TENANT_A, OpportunityInput(requirements={"x": 1}, stage="nueva"))
    # B intenta mover el estado de la oportunidad de A -> no la encuentra.
    assert opportunities.update_opportunity(TENANT_B, opp.id, stage="cotizada") is None
    assert opportunities.get_opportunity(TENANT_A, opp.id).stage == "nueva"
    # A sí puede actualizar estado + importe.
    updated = opportunities.update_opportunity(
        TENANT_A, opp.id, stage="cotizada", estimated_amount=123000)
    assert updated.stage == "cotizada" and updated.estimated_amount == 123000


def test_update_rejects_invalid_stage():
    opp = opportunities.create_or_update_opportunity(
        TENANT_A, OpportunityInput(requirements={}, stage="nueva"))
    with pytest.raises(ValueError):
        opportunities.update_opportunity(TENANT_A, opp.id, stage="inventado")
