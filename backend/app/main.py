"""API del simulador (sandbox). Sólo servidor, sin WhatsApp ni envíos a clientes.

Resolución de empresa: NO se confía un tenant_id arbitrario del cliente. El sandbox
expone un allowlist fijo de empresas demo (A/B) mapeado en el servidor a UUIDs del
seed. En producción el tenant se resolverá por autenticación del panel o asignación
segura del canal, no por este parámetro.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agent import orchestrator, tool_agent
from .agent.tools import ToolContext
from .auth import current_uid
from .config import Settings, settings
from .db import NoMembership, db_healthcheck, user_tx
from .domain import catalog, opportunities
from .schemas import (
    AgentChatRequest,
    AgentConfirmRequest,
    CatalogImportRequest,
    CatalogImportResult,
    ChatRequest,
    ChatResponse,
    MeResponse,
    OpportunitySummary,
    OpportunityUpdate,
    ProductSummary,
)

# Allowlist de empresas demo (sandbox). Coinciden con supabase/seed.sql.
SANDBOX_TENANTS = {
    "A": "0000000a-0000-0000-0000-00000000000a",
    "B": "0000000b-0000-0000-0000-00000000000b",
}

# Fuera de local, verificar JWT contra el Supabase local por omisión rechaza toda sesión
# del panel (401): se avisa al arrancar en vez de descubrirlo request por request.
if settings.app_env != "local" and settings.supabase_url == Settings.model_fields["supabase_url"].default:
    logging.getLogger(__name__).warning(
        "SUPABASE_URL apunta al Supabase local con APP_ENV=%s: el panel /app rechazará "
        "las sesiones del proyecto remoto.", settings.app_env)

app = FastAPI(title="Presupuesto Vivo — Sandbox API", version="0.1.0")

# CORS abierto SÓLO para el sandbox local (la UI se abre como file:// => origin "null").
# En producción restringir a los orígenes del panel autenticado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_tenant(company: str) -> str:
    tenant = SANDBOX_TENANTS.get(company.upper())
    if not tenant:
        raise HTTPException(status_code=400, detail="Empresa demo inválida (usar A o B).")
    return tenant


@app.get("/health")
def health() -> dict:
    ok, detail = db_healthcheck()
    return {
        "status": "ok" if ok else "degraded",
        "db": {"reachable": ok, "detail": detail},
        "app_env": settings.app_env,
        "llm": {"mode": settings.llm_mode_label, "model": settings.llm_model_label},
        # Nunca exponemos credenciales ni la URL completa de la base.
    }


@app.get("/sandbox/products", response_model=list[ProductSummary])
def products(company: str = Query("A"), q: str = Query("")) -> list[ProductSummary]:
    tenant = _resolve_tenant(company)
    return catalog.search_products(tenant, query=q)


@app.post("/sandbox/catalog/import", response_model=CatalogImportResult)
def import_catalog(body: CatalogImportRequest, company: str = Query("A")) -> CatalogImportResult:
    tenant = _resolve_tenant(company)
    imported, errors = catalog.import_items(tenant, [i.model_dump() for i in body.items])
    return CatalogImportResult(imported=imported, errors=errors)


@app.post("/sandbox/chat", response_model=ChatResponse)
def chat(req: ChatRequest, company: str = Query("A")) -> ChatResponse:
    tenant = _resolve_tenant(company)
    return orchestrator.handle_chat(tenant, req.message, req.conversation_id)


@app.get("/sandbox/opportunities", response_model=list[OpportunitySummary])
def opps(company: str = Query("A")) -> list[OpportunitySummary]:
    tenant = _resolve_tenant(company)
    return opportunities.list_opportunities(tenant)


@app.patch("/sandbox/opportunities/{opportunity_id}", response_model=OpportunitySummary)
def update_opp(opportunity_id: str, body: OpportunityUpdate,
               company: str = Query("A")) -> OpportunitySummary:
    tenant = _resolve_tenant(company)
    try:
        updated = opportunities.update_opportunity(
            tenant, opportunity_id, stage=body.stage,
            estimated_amount=body.estimated_amount, next_action_at=body.next_action_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada.")
    return updated


@app.get("/sandbox/opportunities/{opportunity_id}/activity")
def opp_activity(opportunity_id: str, company: str = Query("A")) -> list[dict]:
    """Timeline de la oportunidad: qué se hizo y cuándo (creada, cambios de estado…)."""
    tenant = _resolve_tenant(company)
    return opportunities.get_activity(tenant, opportunity_id)


# --- Agente con tool-calling (Etapa B) ------------------------------------
# El LLM elige las herramientas; el tenant sale del servidor y las ESCRITURAS
# requieren confirmación humana (devuelven pending_action, no se ejecutan solas).
@app.post("/sandbox/agent/chat")
def agent_chat(req: AgentChatRequest, company: str = Query("A")) -> dict:
    tenant = _resolve_tenant(company)
    conv = opportunities.ensure_conversation(tenant, req.conversation_id)
    ctx = ToolContext(tenant_id=tenant, conversation_id=conv)
    registry = tool_agent.build_registry()
    planner = tool_agent.make_planner(registry)
    res = tool_agent.run_agent(ctx, req.message, registry, planner)
    return {
        "reply": res.reply,
        "requires_human": res.requires_human,
        "pending_action": res.pending_action,
        "mode": getattr(planner, "mode", "mock"),
        "conversation_id": conv,
        "trace": [{"name": s.get("name"), "summary": s.get("summary"), "error": s.get("error")}
                  for s in res.trace],
    }


@app.post("/sandbox/agent/confirm")
def agent_confirm(req: AgentConfirmRequest, company: str = Query("A")) -> dict:
    tenant = _resolve_tenant(company)
    conv = opportunities.ensure_conversation(tenant, req.conversation_id)
    ctx = ToolContext(tenant_id=tenant, conversation_id=conv)
    registry = tool_agent.build_registry()
    try:
        result = tool_agent.confirm_action(ctx, req.pending_action, registry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"reply": "Oportunidad registrada.", "opportunity_id": getattr(result, "id", None)}


# --- Panel autenticado (/app/*) -------------------------------------------
# El tenant NO viene del cliente: sale de la membresía del usuario del JWT verificado,
# y cada request corre en UNA transacción `user_tx` (rol app_user, RLS efectivo).
@app.exception_handler(NoMembership)
def _no_membership(_: Request, __: NoMembership) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": "Tu cuenta no tiene un negocio asociado."})


@app.get("/app/me", response_model=MeResponse)
def me(uid: str = Depends(current_uid)) -> MeResponse:
    with user_tx(uid) as (cur, tenant):
        cur.execute("select name from tenants where id = %s", (tenant,))
        row = cur.fetchone()
    return MeResponse(user_id=uid, tenant_id=tenant, business_name=row["name"])


@app.get("/app/opportunities", response_model=list[OpportunitySummary])
def app_opps(uid: str = Depends(current_uid)) -> list[OpportunitySummary]:
    with user_tx(uid) as (cur, tenant):
        return opportunities._list(cur, tenant)


@app.patch("/app/opportunities/{opportunity_id}", response_model=OpportunitySummary)
def app_update_opp(opportunity_id: UUID, body: OpportunityUpdate,
                   uid: str = Depends(current_uid)) -> OpportunitySummary:
    with user_tx(uid) as (cur, tenant):
        try:
            updated = opportunities._update(
                cur, tenant, str(opportunity_id), stage=body.stage,
                estimated_amount=body.estimated_amount, next_action_at=body.next_action_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not updated:
            raise HTTPException(status_code=404, detail="Oportunidad no encontrada.")
        # Auditoría sin PII: sólo qué campos se tocaron.
        opportunities._audit(cur, tenant, "panel_opportunity_updated", updated.id,
                             {"fields": sorted(body.model_dump(exclude_none=True))})
        return updated


@app.get("/app/opportunities/{opportunity_id}/activity")
def app_opp_activity(opportunity_id: UUID, uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        if opportunities._get(cur, tenant, str(opportunity_id)) is None:
            raise HTTPException(status_code=404, detail="Oportunidad no encontrada.")
        return opportunities._activity(cur, tenant, str(opportunity_id))
