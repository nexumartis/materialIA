"""Etapa B — tool-calling real (aditivo, no toca /sandbox/chat).

El LLM (o un planner determinista) elige QUÉ herramienta llamar; el bucle:
- usa SIEMPRE el tenant del contexto, nunca el de los argumentos del modelo,
- sólo ejecuta herramientas de la allowlist,
- NO escribe sin aprobación humana (las escrituras devuelven pending_action)."""
from __future__ import annotations

from app.agent import tool_agent
from app.agent.tools import ToolContext
from app.domain import opportunities

from conftest import TENANT_A, TENANT_B


def _ctx(tenant: str = TENANT_A) -> ToolContext:
    return ToolContext(tenant_id=tenant, conversation_id=None)


class ScriptedPlanner:
    """Planner determinista: devuelve pasos de una lista; al agotarse, finaliza."""
    def __init__(self, steps):
        self._steps = list(steps)

    def next_step(self, message, history):
        return self._steps.pop(0) if self._steps else tool_agent.final("listo")


def test_loop_runs_read_tool_and_finishes():
    reg = tool_agent.build_registry()
    planner = ScriptedPlanner([
        tool_agent.call("buscar_productos", {"category": "mampara", "tipo": "corrediza"}),
        tool_agent.final("Encontré opciones."),
    ])
    res = tool_agent.run_agent(_ctx(), "quiero una mampara", reg, planner)
    assert res.reply == "Encontré opciones."
    assert any(s["name"] == "buscar_productos" for s in res.trace)
    assert res.pending_action is None


def test_write_requires_approval_and_does_not_persist():
    reg = tool_agent.build_registry()
    before = len(opportunities.list_opportunities(TENANT_A, limit=1000))
    planner = ScriptedPlanner([
        tool_agent.call("registrar_oportunidad",
                        {"requirements": {"category": "mampara"}, "stage": "para_cotizar"}),
    ])
    res = tool_agent.run_agent(_ctx(), "registrala", reg, planner)
    assert res.pending_action is not None
    assert res.pending_action["name"] == "registrar_oportunidad"
    after = len(opportunities.list_opportunities(TENANT_A, limit=1000))
    assert after == before  # no se escribió sin aprobación


def test_unknown_tool_is_rejected():
    reg = tool_agent.build_registry()
    planner = ScriptedPlanner([
        tool_agent.call("borrar_todo", {}),
        tool_agent.final("ok"),
    ])
    res = tool_agent.run_agent(_ctx(), "x", reg, planner)
    assert any(s.get("error") for s in res.trace)


def test_tool_uses_context_tenant_not_args():
    reg = tool_agent.build_registry()
    # Intento de pasar otra empresa en los argumentos: se ignora, usa el del contexto.
    planner = ScriptedPlanner([
        tool_agent.call("buscar_productos",
                        {"tenant_id": TENANT_B, "category": "mampara", "tipo": "corrediza"}),
        tool_agent.final("ok"),
    ])
    res = tool_agent.run_agent(_ctx(TENANT_A), "x", reg, planner)
    step = [s for s in res.trace if s["name"] == "buscar_productos"][0]
    assert step["result"]  # devuelve productos de A, no de B


def test_max_steps_caps_the_loop():
    reg = tool_agent.build_registry()

    class Always:
        def next_step(self, message, history):
            return tool_agent.call("buscar_productos", {"category": "mampara"})

    res = tool_agent.run_agent(_ctx(), "x", reg, Always(), max_steps=3)
    reads = [s for s in res.trace if s["name"] == "buscar_productos"]
    assert len(reads) == 3


def test_heuristic_planner_searches_estimates_and_proposes_registration():
    """El planner heurístico (fallback determinista) busca, estima y PROPONE registrar."""
    reg = tool_agent.build_registry()
    planner = tool_agent.HeuristicPlanner()
    res = tool_agent.run_agent(
        _ctx(), "Quiero una mampara corrediza negra de 1,60 x 1,90 en Tigre", reg, planner)
    assert res.pending_action is not None
    assert res.pending_action["name"] == "registrar_oportunidad"
    done = {s.get("name") for s in res.trace}
    assert "buscar_productos" in done and "estimar_cotizacion" in done


def test_confirm_executes_the_write():
    reg = tool_agent.build_registry()
    pending = {"name": "registrar_oportunidad",
               "args": {"requirements": {"category": "mampara", "tipo": "corrediza"},
                        "stage": "para_cotizar"}}
    opp = tool_agent.confirm_action(_ctx(), pending, reg)
    assert opp.id
    assert opportunities.get_opportunity(TENANT_A, opp.id) is not None


def test_agent_endpoints_propose_then_confirm():
    """HTTP: /agent/chat propone la escritura (no la ejecuta) y /agent/confirm la registra."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.post("/sandbox/agent/chat?company=A",
                    json={"message": "Quiero una mampara corrediza negra de 1,60 x 1,90 en Tigre"})
    assert r.status_code == 200
    j = r.json()
    assert j["pending_action"] and j["pending_action"]["name"] == "registrar_oportunidad"

    c = client.post("/sandbox/agent/confirm?company=A",
                    json={"pending_action": j["pending_action"], "conversation_id": j["conversation_id"]})
    assert c.status_code == 200
    assert c.json()["opportunity_id"]
