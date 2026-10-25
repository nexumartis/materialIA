"""API del simulador (sandbox). Sólo servidor, sin WhatsApp ni envíos a clientes.

Resolución de empresa: NO se confía un tenant_id arbitrario del cliente. El sandbox
expone un allowlist fijo de empresas demo (A/B) mapeado en el servidor a UUIDs del
seed. En producción el tenant se resolverá por autenticación del panel o asignación
segura del canal, no por este parámetro.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .agent import orchestrator
from .config import settings
from .db import db_healthcheck
from .domain import catalog, opportunities
from .schemas import (
    CatalogImportRequest,
    CatalogImportResult,
    ChatRequest,
    ChatResponse,
    OpportunitySummary,
    OpportunityUpdate,
    ProductSummary,
)

# Allowlist de empresas demo (sandbox). Coinciden con supabase/seed.sql.
SANDBOX_TENANTS = {
    "A": "0000000a-0000-0000-0000-00000000000a",
    "B": "0000000b-0000-0000-0000-00000000000b",
}

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
