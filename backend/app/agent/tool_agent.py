"""Etapa B — tool-calling real (aditivo; convive con el flujo determinista de /sandbox/chat).

El LLM propone QUÉ herramienta llamar y con qué argumentos de negocio. El bucle garantiza
las reglas innegociables:
- el `tenant_id` sale SIEMPRE del contexto (ToolContext), nunca de los argumentos del modelo;
- sólo se ejecutan herramientas de la allowlist (`build_registry`);
- las ESCRITURAS no se ejecutan solas: devuelven `pending_action` y las confirma una persona
  (`confirm_action`);
- el cotizador sigue sin inventar precios (envuelve `estimate_quote`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from . import tools as T
from .tools import ToolContext
from ..schemas import OpportunityInput, OpportunitySummary, QuoteRequirements

_QUOTE_FIELDS = {"category", "tipo", "color", "material", "ancho_mm", "alto_mm",
                 "localidad", "product_id", "quantity"}


# --- Pasos del planner ----------------------------------------------------
@dataclass
class Step:
    kind: str                       # "tool" | "final"
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    reply: str = ""


def call(name: str, args: Optional[dict[str, Any]] = None) -> Step:
    return Step(kind="tool", name=name, args=args or {})


def final(reply: str) -> Step:
    return Step(kind="final", reply=reply)


class ToolPlanner(Protocol):
    def next_step(self, message: str, history: list[dict[str, Any]]) -> Step: ...


# --- Herramientas (allowlist). Envuelven las tools tenant-safe existentes --
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: Callable[[ToolContext, dict[str, Any]], Any]
    requires_approval: bool = False


def _buscar(ctx: ToolContext, args: dict[str, Any]) -> list[dict[str, str]]:
    filters = {k: args[k] for k in ("category", "tipo", "color", "material") if args.get(k)}
    return [{"id": p.id, "name": p.name} for p in T.search_products(ctx, filters=filters)]


def _estimar(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    req = QuoteRequirements(**{k: v for k, v in args.items() if k in _QUOTE_FIELDS})
    e = T.estimate_quote(ctx, req)
    return {"status": e.status, "requires_human": e.requires_human,
            "amount": e.amount, "missing_fields": e.missing_fields}


def _registrar(ctx: ToolContext, args: dict[str, Any]) -> OpportunitySummary:
    data = OpportunityInput(requirements=args.get("requirements", {}),
                            stage=args.get("stage", "para_cotizar"))
    return T.create_or_update_opportunity(ctx, data)


def build_registry() -> dict[str, Tool]:
    return {t.name: t for t in [
        Tool("buscar_productos",
             "Busca productos del catálogo de la empresa por categoría/tipo/color/material.",
             {"type": "object", "properties": {
                 "category": {"type": "string"}, "tipo": {"type": "string"},
                 "color": {"type": "string"}, "material": {"type": "string"}}},
             _buscar),
        Tool("estimar_cotizacion",
             "Estima la cotización. Nunca inventa precio: a medida ⇒ requires_human.",
             {"type": "object", "properties": {k: {"type": "string"} for k in _QUOTE_FIELDS}},
             _estimar),
        Tool("registrar_oportunidad",
             "Registra/actualiza la oportunidad. Requiere aprobación humana.",
             {"type": "object", "properties": {
                 "requirements": {"type": "object"}, "stage": {"type": "string"}}},
             _registrar, requires_approval=True),
    ]}


# --- Resultado del bucle --------------------------------------------------
@dataclass
class AgentResult:
    reply: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    pending_action: Optional[dict[str, Any]] = None
    requires_human: bool = False


def _summarize(result: Any) -> str:
    if isinstance(result, list):
        return f"{len(result)} resultado(s)"
    return str(result)[:200]


def run_agent(ctx: ToolContext, message: str, registry: dict[str, Tool],
              planner: ToolPlanner, max_steps: int = 6) -> AgentResult:
    """Ejecuta el bucle agéntico. Lecturas se ejecutan; escrituras se gatean por aprobación."""
    trace: list[dict[str, Any]] = []
    for _ in range(max_steps):
        step = planner.next_step(message, trace)
        if step.kind == "final":
            return AgentResult(reply=step.reply or "Listo.", trace=trace)
        tool = registry.get(step.name)
        if tool is None:
            trace.append({"name": step.name, "error": "herramienta no permitida"})
            continue
        if tool.requires_approval:
            return AgentResult(
                reply="Preparé la acción; necesita aprobación humana para registrarse.",
                trace=trace,
                pending_action={"name": step.name, "args": step.args},
                requires_human=True,
            )
        result = tool.run(ctx, step.args)   # el tenant SIEMPRE sale de ctx
        trace.append({"name": step.name, "args": step.args,
                      "result": result, "summary": _summarize(result)})
    return AgentResult(reply="No pude completar el pedido en los pasos disponibles.", trace=trace)


def confirm_action(ctx: ToolContext, pending_action: dict[str, Any],
                   registry: dict[str, Tool]) -> Any:
    """Ejecuta una acción previamente propuesta, tras la aprobación humana. Tenant-safe."""
    tool = registry.get((pending_action or {}).get("name"))
    if tool is None:
        raise ValueError("acción no permitida")
    return tool.run(ctx, pending_action.get("args", {}))


# --- Planners -------------------------------------------------------------
class HeuristicPlanner:
    """Planner determinista (sin LLM). Busca, estima y propone registrar, en ese orden.
    Es el fallback honesto cuando no hay modelo en vivo (mode = 'mock')."""
    mode = "mock"

    def next_step(self, message: str, history: list[dict[str, Any]]) -> Step:
        from .llm_adapter import _parse_requirements
        req, _, name = _parse_requirements(message)
        if name:
            req["customer_name"] = name
        done = {h.get("name") for h in history}
        if "buscar_productos" not in done:
            return call("buscar_productos",
                        {k: req[k] for k in ("category", "tipo", "color", "material") if req.get(k)})
        if "estimar_cotizacion" not in done:
            return call("estimar_cotizacion", dict(req))
        return call("registrar_oportunidad", {"requirements": req, "stage": "para_cotizar"})


class LLMToolPlanner:
    """Planner con tool-calling real: el modelo (Ollama) elige la herramienta. Si el modelo
    falla o no propone una herramienta válida, cae al planner heurístico (progreso garantizado)."""
    mode = "live"

    def __init__(self, registry: dict[str, Tool]):
        self._registry = registry
        self._fallback = HeuristicPlanner()

    def _tools_schema(self) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.parameters,
        }} for t in self._registry.values()]

    def _messages(self, message: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        import json
        sys = ("Sos el asistente de un negocio de cerramientos a medida. Usá las herramientas "
               "para buscar en el catálogo de ESTA empresa y estimar; nunca inventes precios. "
               "Para registrar la oportunidad usá registrar_oportunidad (la confirma una persona). "
               "No pidas ni uses datos de otra empresa.")
        msgs: list[dict[str, Any]] = [{"role": "system", "content": sys},
                                      {"role": "user", "content": message}]
        for h in history:
            if h.get("error"):
                continue
            msgs.append({"role": "assistant", "content": "",
                         "tool_calls": [{"function": {"name": h["name"],
                                                      "arguments": h.get("args", {})}}]})
            msgs.append({"role": "tool",
                         "content": json.dumps(h.get("summary") or str(h.get("result")))})
        return msgs

    def next_step(self, message: str, history: list[dict[str, Any]]) -> Step:
        # Guardarraíl de progreso/costo: el modelo lidera los primeros pasos; si no propone
        # una escritura a tiempo, el plan determinista cierra (evita que itere sin avanzar).
        nonerr = [h for h in history if not h.get("error")]
        if len(nonerr) >= 2:
            return self._fallback.next_step(message, history)
        try:
            import json
            import httpx
            from ..config import settings
            payload = {
                "model": settings.ollama_model,
                "messages": self._messages(message, history),
                "tools": self._tools_schema(),
                "stream": False,
                "think": False,
            }
            headers = {}
            key = settings.ollama_api_key or settings.llm_api_key
            if key:
                headers["Authorization"] = f"Bearer {key}"
            resp = httpx.post(f"{settings.ollama_base_url}/api/chat", json=payload,
                              headers=headers, timeout=settings.llm_timeout_s)
            resp.raise_for_status()
            msg = resp.json().get("message", {})
            calls = msg.get("tool_calls") or []
            if calls:
                fn = calls[0].get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                if name in self._registry:
                    # Si repite la misma herramienta del último paso, no avanza: plan determinista.
                    if nonerr and nonerr[-1].get("name") == name:
                        return self._fallback.next_step(message, history)
                    return call(name, args)
            content = (msg.get("content") or "").strip()
            done = {h.get("name") for h in nonerr}
            # Sólo aceptamos un cierre del modelo DESPUÉS de haber estimado; un cierre
            # prematuro (p. ej. porque una búsqueda dio 0) no corta el flujo de cotización.
            if content and "estimar_cotizacion" in done:
                return final(content)
        except Exception:
            pass
        # Sin herramienta útil: seguimos con el plan determinista (garantiza avanzar).
        return self._fallback.next_step(message, history)


def make_planner(registry: dict[str, Tool]) -> ToolPlanner:
    """Elige el planner según la config: LLM en vivo (ollama) o heurístico determinista."""
    from ..config import settings
    if settings.llm_provider == "ollama":
        return LLMToolPlanner(registry)
    return HeuristicPlanner()
