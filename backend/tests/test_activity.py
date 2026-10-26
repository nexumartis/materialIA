"""Actividad (timeline) de oportunidades: el agente y el panel dejan registro de lo
que hacen, y se aplican reglas de seguimiento por etapa. Todo scoped por tenant."""
from __future__ import annotations

from app.domain import opportunities
from app.schemas import OpportunityInput

from conftest import TENANT_C, TENANT_D


def _new_opp(tenant: str):
    return opportunities.create_or_update_opportunity(
        tenant, OpportunityInput(requirements={"producto": "Canilla de cocina"}, stage="nueva"))


def test_creating_opportunity_logs_activity():
    """Crear una oportunidad deja un registro 'creada' en su actividad."""
    opp = _new_opp(TENANT_C)
    kinds = [a["kind"] for a in opportunities.get_activity(TENANT_C, opp.id)]
    assert "creada" in kinds


def test_stage_change_logs_transition():
    """Cambiar el estado registra la transición con el destino en el detalle."""
    opp = _new_opp(TENANT_C)
    opportunities.update_opportunity(TENANT_C, opp.id, stage="para_cotizar")
    transitions = [a for a in opportunities.get_activity(TENANT_C, opp.id)
                   if a["kind"] == "cambio_estado"]
    assert transitions, "debe registrar el cambio de estado"
    assert "para_cotizar" in transitions[-1]["detail"]


def test_unchanged_stage_logs_no_transition():
    """Actualizar sólo el importe (sin tocar el estado) no registra una transición."""
    opp = _new_opp(TENANT_C)
    opportunities.update_opportunity(TENANT_C, opp.id, estimated_amount=1000)
    transitions = [a for a in opportunities.get_activity(TENANT_C, opp.id)
                   if a["kind"] == "cambio_estado"]
    assert transitions == []


def test_closing_clears_followup():
    """Cerrar una oportunidad limpia su seguimiento (una cerrada no 'vence')."""
    opp = _new_opp(TENANT_C)
    assert opp.next_action_at is not None  # nace con seguimiento a +2 días
    closed = opportunities.update_opportunity(TENANT_C, opp.id, stage="cerrada")
    assert closed is not None
    assert closed.next_action_at is None


def test_activity_is_tenant_isolated():
    """Otra empresa no ve la actividad de una oportunidad ajena."""
    opp = _new_opp(TENANT_C)
    assert opportunities.get_activity(TENANT_D, opp.id) == []


def test_activity_endpoint_returns_timeline():
    """GET /sandbox/opportunities/{id}/activity devuelve el timeline de la oportunidad."""
    from fastapi.testclient import TestClient
    from app.main import app

    opp = _new_opp(TENANT_C)
    act = TestClient(app).get(f"/sandbox/opportunities/{opp.id}/activity?company=C")
    assert act.status_code == 200
    assert "creada" in [a["kind"] for a in act.json()]
