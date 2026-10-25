"""Actividad (timeline) de oportunidades: el agente y el panel dejan registro de lo
que hacen, y se aplican reglas de seguimiento por etapa. Todo scoped por tenant."""
from __future__ import annotations

from app.agent import orchestrator
from app.domain import opportunities
from app.schemas import OpportunityInput

from conftest import TENANT_A, TENANT_B


def _new_opp(tenant: str):
    return opportunities.create_or_update_opportunity(
        tenant, OpportunityInput(requirements={"category": "mampara"}, stage="nueva"))


def test_creating_opportunity_logs_activity():
    """Crear una oportunidad deja un registro 'creada' en su actividad."""
    opp = _new_opp(TENANT_A)
    kinds = [a["kind"] for a in opportunities.get_activity(TENANT_A, opp.id)]
    assert "creada" in kinds


def test_stage_change_logs_transition():
    """Cambiar el estado registra la transición con el destino en el detalle."""
    opp = _new_opp(TENANT_A)
    opportunities.update_opportunity(TENANT_A, opp.id, stage="para_cotizar")
    transitions = [a for a in opportunities.get_activity(TENANT_A, opp.id)
                   if a["kind"] == "cambio_estado"]
    assert transitions, "debe registrar el cambio de estado"
    assert "para_cotizar" in transitions[-1]["detail"]


def test_unchanged_stage_logs_no_transition():
    """Actualizar sólo el importe (sin tocar el estado) no registra una transición."""
    opp = _new_opp(TENANT_A)
    opportunities.update_opportunity(TENANT_A, opp.id, estimated_amount=1000)
    transitions = [a for a in opportunities.get_activity(TENANT_A, opp.id)
                   if a["kind"] == "cambio_estado"]
    assert transitions == []


def test_closing_clears_followup():
    """Cerrar una oportunidad limpia su seguimiento (una cerrada no 'vence')."""
    opp = _new_opp(TENANT_A)
    assert opp.next_action_at is not None  # nace con seguimiento a +2 días
    closed = opportunities.update_opportunity(TENANT_A, opp.id, stage="cerrada")
    assert closed is not None
    assert closed.next_action_at is None


def test_activity_is_tenant_isolated():
    """Otra empresa no ve la actividad de una oportunidad ajena."""
    opp = _new_opp(TENANT_A)
    assert opportunities.get_activity(TENANT_B, opp.id) == []


def test_agent_logs_stage_advance_across_turns():
    """El agente, al acumular datos y avanzar el lead entre turnos, lo deja en el timeline."""
    r1 = orchestrator.handle_chat(TENANT_A, "Hola, quiero una mampara corrediza negra")
    conv = r1.conversation_id
    orchestrator.handle_chat(TENANT_A, "Mide 1,60 x 1,90 y estoy en Tigre", conversation_id=conv)
    transitions = [a for a in opportunities.get_activity(TENANT_A, r1.opportunity_id)
                   if a["kind"] == "cambio_estado"]
    assert transitions, "el agente debe registrar que avanzó el lead"
    assert "para_cotizar" in transitions[-1]["detail"]


def test_activity_endpoint_returns_timeline():
    """GET /sandbox/opportunities/{id}/activity devuelve el timeline de la oportunidad."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/sandbox/chat?company=A",
        json={"message": "Quiero una mampara corrediza negra de 1,60 x 1,90 en Tigre",
              "conversation_id": None},
    )
    opp_id = r.json()["opportunity_id"]
    assert opp_id

    act = client.get(f"/sandbox/opportunities/{opp_id}/activity?company=A")
    assert act.status_code == 200
    assert "creada" in [a["kind"] for a in act.json()]
