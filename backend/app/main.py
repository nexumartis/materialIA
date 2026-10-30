"""API del agente de ventas: sandbox (sin cuenta), webhooks de pago y panel autenticado.
Sin WhatsApp ni envíos a clientes reales en esta fase.

Resolución de empresa: NO se confía un tenant_id arbitrario del cliente. El sandbox
expone un allowlist fijo de empresas demo (C/D) mapeado en el servidor a UUIDs del
seed. En producción el tenant se resolverá por autenticación del panel o asignación
segura del canal, no por este parámetro.
"""
from __future__ import annotations

import logging
from uuid import UUID

import psycopg

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles

from . import buyer_session
from .agent import sales_agent
from .auth import current_uid
from .config import Settings, settings
from .db import NoMembership, db_healthcheck, tenant_tx, user_tx
from .documents import ocr, store as documents
from .domain import (agent_profile, backoffice, catalog, catalog_sheet, customer_memory, evals, inbox, knowledge,
                     opportunities, orders, receipts)
from .payments import service as payments
from .payments.providers import SimulatedProvider
from .schemas import (
    CatalogImportRequest,
    CatalogImportResult,
    ChatRequest,
    MeResponse,
    OpportunitySummary,
    OpportunityUpdate,
    AgentPreview,
    HumanReply,
    ProductSummary,
    TransferConfirm,
)

# Allowlist de empresas demo (sandbox). Coinciden con supabase/seed.sql.
SANDBOX_TENANTS = {
    "C": "0000000c-0000-0000-0000-00000000000c",   # grifería: agente de ventas
    "D": "0000000d-0000-0000-0000-00000000000d",   # ferretería: segunda empresa (aislamiento)
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
# Fotos de producto de la demo (ilustraciones propias). Los canales reciben URL absoluta.
app.mount("/static", StaticFiles(directory=str(__import__("pathlib").Path(__file__).parent / "static")),
          name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Error-Code"],   # código estructurado de error (p. ej. evals_failed)
)


def _resolve_tenant(company: str) -> str:
    tenant = SANDBOX_TENANTS.get(company.upper())
    if not tenant:
        raise HTTPException(status_code=400, detail="Empresa demo inválida (usar C o D).")
    return tenant


# Las empresas demo C/D también tienen tienda pública: el sandbox (sin cuenta) no lee ni opera los
# pedidos y oportunidades de conversaciones de compradores, y sus mutaciones administrativas sólo
# existen en local. La lectura demo y el chat demo siguen disponibles.
def _sandbox_admin() -> None:
    if not settings.sandbox_admin_enabled:
        raise HTTPException(status_code=404, detail="No disponible fuera del entorno local.")


def _not_buyer_record(table: str, tenant: str, record_id: str, detail: str) -> None:
    if buyer_session.in_public_thread(table, tenant, record_id):
        raise HTTPException(status_code=404, detail=detail)


@app.get("/health")
def health() -> dict:
    ok, detail = db_healthcheck()
    return {
        "status": "ok" if ok else "degraded",
        "db": {"reachable": ok, "detail": detail},
        "app_env": settings.app_env,
        "llm": {"mode": settings.llm_mode_label, "model": settings.llm_model_label},
        "payments": {"provider": settings.payment_provider},
        # Nunca exponemos credenciales ni la URL completa de la base.
    }


@app.get("/sandbox/products", response_model=list[ProductSummary])
def products(company: str = Query("C"), q: str = Query("")) -> list[ProductSummary]:
    tenant = _resolve_tenant(company)
    return catalog.search_products(tenant, query=q)


@app.post("/sandbox/catalog/import", response_model=CatalogImportResult)
def import_catalog(body: CatalogImportRequest, company: str = Query("C")) -> CatalogImportResult:
    _sandbox_admin()
    tenant = _resolve_tenant(company)
    imported, errors = catalog.import_items(tenant, [i.model_dump() for i in body.items])
    return CatalogImportResult(imported=imported, errors=errors)


@app.get("/sandbox/opportunities", response_model=list[OpportunitySummary])
def opps(company: str = Query("C")) -> list[OpportunitySummary]:
    tenant = _resolve_tenant(company)
    return opportunities.list_opportunities(tenant, exclude_buyer_threads=True)


@app.patch("/sandbox/opportunities/{opportunity_id}", response_model=OpportunitySummary)
def update_opp(opportunity_id: str, body: OpportunityUpdate,
               company: str = Query("C")) -> OpportunitySummary:
    _sandbox_admin()
    tenant = _resolve_tenant(company)
    _not_buyer_record("opportunities", tenant, opportunity_id, "Oportunidad no encontrada.")
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
def opp_activity(opportunity_id: str, company: str = Query("C")) -> list[dict]:
    """Timeline de la oportunidad: qué se hizo y cuándo (creada, cambios de estado…)."""
    tenant = _resolve_tenant(company)
    _not_buyer_record("opportunities", tenant, opportunity_id, "Oportunidad no encontrada.")
    return opportunities.get_activity(tenant, opportunity_id)


# --- Agente de ventas (empresa demo C) -------------------------------------
# Stock, carrito, pedido y link de pago desde el chat. El pago SÓLO se confirma con el aviso
# verificado del proveedor (webhook + consulta del pago), nunca por lo que diga el cliente.
def _not_public(tenant: str, conversation_id: str | None) -> None:
    """El sandbox no es un acceso alternativo a las conversaciones de la tienda pública."""
    if conversation_id and buyer_session.is_public(tenant, conversation_id):
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")


@app.post("/sandbox/sales/chat")
def sales_chat(req: ChatRequest, company: str = Query("C")) -> dict:
    tenant = _resolve_tenant(company)
    _not_public(tenant, req.conversation_id)
    res = sales_agent.handle_sales_message(tenant, req.message, req.conversation_id)
    return {
        "reply": res.reply, "conversation_id": res.conversation_id, "mode": res.mode,
        "requires_human": res.requires_human, "cart": res.cart, "orders": res.orders,
        "payment": res.payment, "products": res.products, "trace": res.trace, "ui": res.ui,
    }


@app.get("/sandbox/sales/{conversation_id}")
def sales_conversation(conversation_id: UUID, company: str = Query("C")) -> dict:
    """Estado actual de la conversación de venta (mensajes, carrito y pedidos). El chat lo relee
    al volver del checkout: el aviso de pago confirmado llega por acá, como llegaría por WhatsApp."""
    tenant = _resolve_tenant(company)
    conv = str(conversation_id)
    _not_public(tenant, conv)
    return {
        "messages": opportunities.conversation_messages(tenant, conv),
        "cart": orders.get_cart(tenant, conv),
        "orders": orders.conversation_orders(tenant, conv),
        "attended_by_human": inbox.is_taken(tenant, conv),
    }


@app.get("/sandbox/orders/{order_id}")
def sandbox_order(order_id: UUID, company: str = Query("C")) -> dict:
    tenant = _resolve_tenant(company)
    _not_buyer_record("orders", tenant, str(order_id), "Pedido no encontrado.")
    order = orders.get_order(tenant, str(order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    return order


@app.post("/sandbox/orders/{order_id}/status")
def sandbox_order_status(order_id: UUID, status: str = Query(...), company: str = Query("C")) -> dict:
    """Avance operativo (preparación, despacho, entrega) que hará el negocio desde el panel."""
    _sandbox_admin()
    tenant = _resolve_tenant(company)
    _not_buyer_record("orders", tenant, str(order_id), "Pedido no encontrado.")
    try:
        order = orders.advance_status(tenant, str(order_id), status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    return order


@app.post("/sandbox/maintenance/expire-reservations")
def sandbox_expire() -> dict:
    """Lo mismo que hace el worker (`python -m app.worker`) en cada vuelta."""
    _sandbox_admin()
    return {"expired": orders.expire_reservations()}


_SIM_PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Checkout simulado</title>
<style>body{{font-family:system-ui,sans-serif;max-width:420px;margin:40px auto;padding:0 16px;color:#1b1b1b}}
.tag{{background:#fff3cd;border:1px solid #e0c36a;padding:8px 10px;border-radius:8px;font-size:14px}}
button{{font-size:16px;padding:10px 14px;border-radius:8px;border:1px solid #888;margin:6px 6px 0 0;cursor:pointer}}
.ok{{background:#1f7a3a;color:#fff;border-color:#1f7a3a}}</style></head><body>
<p class="tag">Checkout <b>SIMULADO</b> de prueba. No es Mercado Pago y no se cobra nada.</p>
<h2>Pedido #{number}</h2><p>Total: <b>{total}</b></p>{body}</body></html>"""


def _sim_order(preference_id: str) -> dict:
    from .db import system_tx
    if settings.payment_provider != "simulated":
        raise HTTPException(status_code=404, detail="Checkout simulado deshabilitado.")
    with system_tx() as cur:
        cur.execute("select tenant_id, order_id from payments where provider = 'simulated' "
                    "and preference_id = %s", (preference_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Link de pago inexistente.")
    return orders.get_order(str(row["tenant_id"]), str(row["order_id"]))


@app.get("/sandbox/checkout/{preference_id}", response_class=HTMLResponse)
def sim_checkout_page(preference_id: str) -> str:
    order = _sim_order(preference_id)
    body = (f'<form method="post" action="/sandbox/checkout/{preference_id}/pay?outcome=approved">'
            '<button class="ok">Pagar (aprobado)</button></form>'
            f'<form method="post" action="/sandbox/checkout/{preference_id}/pay?outcome=rejected">'
            '<button>Simular pago rechazado</button></form>')
    total = "$" + f"{order['total']:,.0f}".replace(",", ".")
    return _SIM_PAGE.format(number=order["number"], total=total, body=body)


@app.post("/sandbox/checkout/{preference_id}/pay", response_class=HTMLResponse)
def sim_checkout_pay(preference_id: str, outcome: str = Query("approved")) -> str:
    """El comprador paga en el checkout simulado; el "proveedor" manda su aviso firmado al mismo
    procesador que usa Mercado Pago (firma → consulta del pago → aplicación idempotente)."""
    _sim_order(preference_id)   # 404 si el simulado no es el proveedor configurado
    try:
        headers, body = SimulatedProvider().pay(preference_id, outcome)
    except LookupError:
        raise HTTPException(status_code=404, detail="Link de pago inexistente.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _, result = payments.receive_notification("simulated", headers, {}, body)
    order = _sim_order(preference_id)
    total = "$" + f"{order['total']:,.0f}".replace(",", ".")
    msg = ("<p><b>Pago aprobado.</b> Volvé al chat: el pedido ya figura como pagado.</p>"
           if order["status"] == "PAID" else f"<p>Resultado: {result}. Podés volver a intentar.</p>")
    return _SIM_PAGE.format(number=order["number"], total=total, body=msg)


@app.post("/webhooks/{provider}")
async def payment_webhook(provider: str, request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        body = {}
    status, result = payments.receive_notification(
        provider, dict(request.headers), dict(request.query_params),
        body if isinstance(body, dict) else {})
    return JSONResponse(status_code=status, content={"result": result})


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


# --- Panel: el negocio arma su agente ---------------------------------------
def _business_name(cur, tenant: str) -> str:
    cur.execute("select name from tenants where id = %s", (tenant,))
    return cur.fetchone()["name"]


@app.get("/app/agent-templates")
def app_agent_templates(uid: str = Depends(current_uid)) -> list[dict]:
    return [{"key": k, "label": t["label"]} for k, t in agent_profile.TEMPLATES.items()]


@app.get("/app/agent-templates/{key}")
def app_agent_template(key: str, uid: str = Depends(current_uid)) -> dict:
    """Contenido de la plantilla de un rubro SIN aplicarla (el asistente la vuelca en su borrador).
    No incluye envíos, horarios ni medios de pago: eso es del negocio, no del rubro."""
    if key not in agent_profile.TEMPLATES:
        raise HTTPException(status_code=404, detail="Rubro inexistente.")
    with user_tx(uid) as (cur, tenant):
        t = agent_profile.template_profile(key, _business_name(cur, tenant))
    return {k: t[k] for k in ("business_type", "seller_name", "tone", "greeting", "faq", "rules")}


@app.get("/app/agent-profile")
def app_get_profile(uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        return agent_profile._ensure(cur, tenant, _business_name(cur, tenant))


@app.put("/app/agent-profile")
def app_put_profile(body: dict = Body(...), uid: str = Depends(current_uid)) -> dict:
    """Guarda el formulario. Con `apply_template`, precarga la plantilla del rubro elegido."""
    with user_tx(uid) as (cur, tenant):
        agent_profile._ensure(cur, tenant, _business_name(cur, tenant))
        data = dict(body)
        if data.pop("apply_template", False):
            data = {**agent_profile.template_profile(data.get("business_type", "generico"),
                                                     _business_name(cur, tenant)), **{
                k: v for k, v in data.items() if k == "public_slug"}}
        require_evals = bool(data.pop("require_evals", False))
        try:
            changes = agent_profile.validate(data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        # Con pruebas cargadas, una versión que no las pasa no se activa (el dueño puede forzarlo).
        if require_evals:
            cases = evals.list_cases(cur, tenant)
            if cases:
                result = evals.run(tenant, cases, {**agent_profile._get(cur, tenant), **changes})
                if result["passed"] < result["total"]:
                    raise HTTPException(status_code=409, headers={"X-Error-Code": "evals_failed"}, detail=(
                        f"No se guardó: {result['total'] - result['passed']} de {result['total']} pruebas "
                        "fallaron. Revisalas con «Probar» o guardá igual."))
        # El link es único entre TODOS los negocios; bajo RLS no se ven los ajenos, así que lo
        # decide la restricción única de la base.
        try:
            with cur.connection.transaction():
                profile = agent_profile._update(cur, tenant, changes, uid)
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=409, detail="Ese link ya lo usa otro negocio.")
        opportunities._audit(cur, tenant, "agent_profile_updated", None, {"fields": sorted(changes)})
        return profile


@app.get("/app/agent-tools")
def app_agent_tools(uid: str = Depends(current_uid)) -> list[dict]:
    """Herramientas que el negocio puede apagar (buscar, consultar y carrito son fijas)."""
    return [{"key": k, "label": v} for k, v in agent_profile.TOGGLEABLE_TOOLS.items()]


@app.get("/app/agent-profile/versions")
def app_profile_versions(uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        return agent_profile.list_versions(cur, tenant)


@app.post("/app/agent-profile/versions/{version}/restore")
def app_profile_restore(version: int, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        profile = agent_profile.restore(cur, tenant, version, uid)
        if profile is None:
            raise HTTPException(status_code=404, detail="Versión no encontrada.")
        opportunities._audit(cur, tenant, "agent_profile_restored", None,
                             {"from_version": version, "new_version": profile["version"]})
        return profile


@app.get("/app/catalog")
def app_catalog(uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        return backoffice.list_catalog(cur, tenant)


@app.patch("/app/catalog/{item_id}")
def app_update_product(item_id: UUID, body: dict = Body(...), uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        try:
            item = backoffice.update_product(
                cur, tenant, str(item_id),
                price=float(body["price"]) if body.get("price") is not None else None,
                stock=int(body["stock"]) if body.get("stock") is not None else None,
                active=bool(body["active"]) if body.get("active") is not None else None)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if item is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")
        opportunities._audit(cur, tenant, "catalog_item_updated", str(item_id),
                             {"fields": sorted(k for k in ("price", "stock", "active") if body.get(k) is not None)})
        return item


# --- Panel: catálogo desde Google Sheets -------------------------------------------
@app.get("/app/catalog/sheet")
def app_catalog_sheet(uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        return {"sheet": catalog_sheet.get(cur, tenant)}


@app.put("/app/catalog/sheet")
def app_connect_catalog_sheet(body: dict = Body(...), uid: str = Depends(current_uid)) -> dict:
    """Conecta (o reemplaza) la planilla y la sincroniza en el momento."""
    with user_tx(uid) as (cur, tenant):
        try:
            catalog_sheet.connect(cur, tenant, uid, str(body.get("url") or ""))
        except catalog_sheet.SheetError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return {"sheet": catalog_sheet.sync(tenant)}


@app.post("/app/catalog/sheet/sync")
def app_sync_catalog_sheet(uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (_, tenant):
        pass   # el negocio sale de la membresía; la lectura la hace el backend (red fuera de la transacción)
    sheet = catalog_sheet.sync(tenant)
    if sheet is None:
        raise HTTPException(status_code=404, detail="No hay una planilla conectada.")
    return {"sheet": sheet}


@app.delete("/app/catalog/sheet")
def app_disconnect_catalog_sheet(uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        return {"disconnected": catalog_sheet.disconnect(cur, tenant, uid)}


@app.post("/app/catalog/import")
def app_import_catalog(body: dict = Body(...), uid: str = Depends(current_uid)) -> dict:
    """CSV como texto (el front lo lee del archivo). Devuelve creados, actualizados y errores por fila."""
    text = str(body.get("csv") or "")
    if len(text) > 2_000_000:
        raise HTTPException(status_code=413, detail="El archivo es demasiado grande (máx. 2 MB).")
    with user_tx(uid) as (cur, tenant):
        try:
            result = backoffice.import_csv(cur, tenant, text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        opportunities._audit(cur, tenant, "catalog_imported", None,
                             {"created": result["created"], "updated": result["updated"],
                              "errors": len(result["errors"])})
        return result


@app.get("/app/orders")
def app_orders(uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        return backoffice.list_orders(cur, tenant)


@app.post("/app/orders/{order_id}/status")
def app_order_status(order_id: UUID, status: str = Query(...), uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        try:
            order = backoffice.advance_order(cur, tenant, str(order_id), status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if order is None:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        opportunities._audit(cur, tenant, "order_status_changed", str(order_id), {"status": status})
        return order


# --- Panel: bandeja de conversaciones y toma de control humana ----------------------
@app.get("/app/inbox")
def app_inbox(filter: str = Query("todas", description="todas | derivadas | con_pedido | sin_responder | mias"),
              uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        try:
            return inbox.list_conversations(cur, tenant, uid, filter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@app.get("/app/inbox/{conversation_id}")
def app_inbox_detail(conversation_id: UUID, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        found = inbox.detail(cur, tenant, uid, str(conversation_id))
    if found is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return found


def _inbox_action(conversation_id: UUID, uid: str, action) -> dict:
    conv = str(conversation_id)
    try:
        with user_tx(uid) as (cur, tenant):
            if not action(cur, tenant, uid, conv):
                raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    except inbox.TakenByOther as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    # Tomar o devolver invalida lo que el agente dejó pendiente (oferta, compra por confirmar).
    inbox.forget_pending_turn(tenant, conv)
    with user_tx(uid) as (cur, tenant):
        return inbox.detail(cur, tenant, uid, conv)


@app.post("/app/inbox/{conversation_id}/take")
def app_inbox_take(conversation_id: UUID, uid: str = Depends(current_uid)) -> dict:
    return _inbox_action(conversation_id, uid, inbox.take)


@app.post("/app/inbox/{conversation_id}/release")
def app_inbox_release(conversation_id: UUID, uid: str = Depends(current_uid)) -> dict:
    return _inbox_action(conversation_id, uid, inbox.release)


@app.post("/app/inbox/{conversation_id}/reply")
def app_inbox_reply(conversation_id: UUID, req: HumanReply, uid: str = Depends(current_uid)) -> dict:
    try:
        return _inbox_action(conversation_id, uid, lambda cur, t, u, c: inbox.reply(cur, t, u, c, req.text))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Panel: comprobantes, transferencias y registro mensual --------------------------
# El dueño revisa los archivos y acredita sólo lo que cotejó en su banco (confirm_transfer).
@app.get("/app/payment-documents")
def app_payment_documents(month: str = Query(..., description="AAAA-MM, hora Argentina"),
                          uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        try:
            return documents.list_month(cur, tenant, month)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@app.get("/app/payment-documents/{document_id}/original")
def app_payment_document_original(document_id: UUID, uid: str = Depends(current_uid)) -> Response:
    with user_tx(uid) as (cur, tenant):
        found = documents.original(cur, tenant, str(document_id))
    if found is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    mime, content = found
    ext = {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}[mime]
    return Response(content, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="comprobante-{document_id}.{ext}"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@app.post("/app/payment-documents/{document_id}/reject")
def app_payment_document_reject(document_id: UUID, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        if not documents.reject(cur, tenant, uid, str(document_id)):
            raise HTTPException(status_code=404, detail="Comprobante no encontrado o ya asociado a un pago.")
        opportunities._audit(cur, tenant, "payment_document_rejected", str(document_id), {"actor": uid})
    return {"rejected": True}


@app.post("/app/orders/{order_id}/confirm-transfer")
def app_confirm_transfer(order_id: UUID, req: TransferConfirm, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (_, tenant):
        pass   # el negocio sale de la membresía; confirm_transfer la revalida al bloquear el pedido
    try:
        outcome = payments.confirm_transfer(tenant, uid, str(order_id), req.reference, req.amount,
                                            req.currency, [str(d) for d in req.document_ids])
    except payments.ReferenceInUse as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Tu cuenta no tiene acceso a este negocio.")
    except LookupError:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"outcome": outcome, "order": orders.get_order(tenant, str(order_id))}


@app.get("/app/payments/register.csv")
def app_payment_register(month: str = Query(..., description="AAAA-MM, hora Argentina"),
                         uid: str = Depends(current_uid)) -> Response:
    with user_tx(uid) as (cur, tenant):
        try:
            body = documents.month_csv(cur, tenant, month)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return Response(body, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="pagos-{month}.csv"', "Cache-Control": "private, no-store"})


@app.get("/app/orders/{order_id}/receipt.pdf")
def app_receipt_pdf(order_id: UUID, uid: str = Depends(current_uid)) -> Response:
    with user_tx(uid) as (cur, tenant):
        receipt = receipts.get(cur, tenant, str(order_id))
    return _receipt_pdf(receipt)


# --- Link público del agente de cada negocio ---------------------------------
# El negocio sale del slug (identificador público de la tienda) resuelto en el servidor.
def _store(slug: str) -> dict:
    store = agent_profile.tenant_by_slug(slug)
    if store is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    return store


@app.get("/public/{slug}")
def public_store(slug: str) -> dict:
    store = _store(slug)
    profile = agent_profile.for_agent(store["tenant_id"]) or {}
    return {"name": store["name"], "seller_name": profile.get("seller_name"),
            "greeting": profile.get("greeting"), "payments": settings.payment_provider}


# Cada conversación pertenece al comprador que la empezó: el token emitido al crearla viaja en el
# header `X-Conversation-Token` y se exige en cada lectura y escritura (ver buyer_session.py).
# Una UUID ajena, de otro negocio o sin token da el mismo 404 que una inexistente.
def _owned(tenant: str, conversation_id: str, token: str | None) -> None:
    if not buyer_session.owns(tenant, conversation_id, token):
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")


# Memoria del cliente en la tienda web: el navegador genera una clave aleatoria y la manda en
# `X-Buyer-Key`; el servidor guarda sólo SHA-256(negocio + clave). Sin clave, no hay memoria.
BUYER_KEY = "X-Buyer-Key"


@app.post("/public/{slug}/chat")
def public_chat(slug: str, req: ChatRequest,
                token: str | None = Header(None, alias=buyer_session.HEADER),
                buyer_key: str | None = Header(None, alias=BUYER_KEY)) -> dict:
    store = _store(slug)
    tenant = store["tenant_id"]
    new_token = None
    if req.conversation_id:
        _owned(tenant, req.conversation_id, token)
        conv = req.conversation_id
    else:
        conv, new_token = buyer_session.start(tenant)
    if buyer_key:
        customer = customer_memory.identify(tenant, "web", buyer_key)
        if customer:
            customer_memory.link_conversation(tenant, conv, customer)
    res = sales_agent.handle_sales_message(tenant, req.message, conv)
    # El token se entrega sólo al crear la conversación.
    return {"reply": res.reply, "conversation_id": res.conversation_id, "conversation_token": new_token,
            "mode": res.mode, "requires_human": res.requires_human, "cart": res.cart, "orders": res.orders,
            "payment": res.payment, "trace": res.trace, "ui": res.ui}


@app.delete("/public/{slug}/me")
def public_forget_me(slug: str, buyer_key: str | None = Header(None, alias=BUYER_KEY)) -> dict:
    """"Olvidarme": borra lo que el negocio recuerda de este comprador en este navegador."""
    store = _store(slug)
    tenant = store["tenant_id"]
    # Sólo busca: "olvidarme" con una clave desconocida no crea un cliente.
    customer = customer_memory.identify(tenant, "web", buyer_key or "", create=False) if buyer_key else None
    return {"forgotten": customer_memory.forget(tenant, customer)}


@app.get("/public/{slug}/conversations/{conversation_id}")
def public_conversation(slug: str, conversation_id: UUID,
                        token: str | None = Header(None, alias=buyer_session.HEADER)) -> dict:
    store = _store(slug)
    conv = str(conversation_id)
    _owned(store["tenant_id"], conv, token)
    return {"messages": opportunities.conversation_messages(store["tenant_id"], conv),
            "cart": orders.get_cart(store["tenant_id"], conv),
            "orders": orders.conversation_orders(store["tenant_id"], conv),
            "documents": documents.for_conversation(store["tenant_id"], conv),
            "attended_by_human": inbox.is_taken(store["tenant_id"], conv)}


@app.post("/public/{slug}/conversations/{conversation_id}/orders/{order_id}/documents")
async def public_upload_document(slug: str, conversation_id: UUID, order_id: UUID, request: Request,
                                 token: str | None = Header(None, alias=buyer_session.HEADER)) -> dict:
    """Comprobante de pago (JPG/PNG/PDF) como cuerpo crudo. Queda para que el negocio lo revise:
    recibirlo o leerlo NO acredita el pago."""
    store = await run_in_threadpool(_store, slug)
    tenant, conv = store["tenant_id"], str(conversation_id)
    await run_in_threadpool(_owned, tenant, conv, token)   # antes de leer el archivo
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        raise HTTPException(status_code=400, detail="Content-Length inválido.")
    too_big = HTTPException(status_code=413, detail=f"El archivo supera {ocr.MAX_BYTES // (1024 * 1024)} MiB.")
    if declared > ocr.MAX_BYTES:
        raise too_big
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > ocr.MAX_BYTES:
            raise too_big
    try:
        doc = await run_in_threadpool(documents.receive, tenant, conv, str(order_id), bytes(data))
    except ocr.DocumentRejected as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    except (documents.DuplicateDocument, documents.TooManyDocuments) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except LookupError:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    return {"document": doc, "note": "Recibimos tu comprobante. El negocio lo revisa antes de confirmar el pago."}


def _receipt_pdf(receipt: dict | None) -> Response:
    if receipt is None:
        raise HTTPException(status_code=404, detail="Constancia no encontrada.")
    return Response(receipts.render_pdf(receipt), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="constancia-pedido-{receipt["order_number"]}.pdf"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@app.get("/public/{slug}/conversations/{conversation_id}/receipts/{receipt_id}/pdf")
def public_receipt_pdf(slug: str, conversation_id: UUID, receipt_id: UUID,
                       token: str | None = Header(None, alias=buyer_session.HEADER)) -> Response:
    """Constancia de compra del comprador (sólo de los pedidos de SU conversación)."""
    store = _store(slug)
    tenant, conv = store["tenant_id"], str(conversation_id)
    _owned(tenant, conv, token)
    with tenant_tx(tenant) as cur:
        return _receipt_pdf(receipts.in_conversation(cur, tenant, conv, str(receipt_id)))


# --- Panel: base de conocimiento y evaluaciones del agente ---------------------
@app.get("/app/knowledge")
def app_knowledge(uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        return knowledge.list_documents(cur, tenant)


@app.post("/app/knowledge")
def app_add_knowledge(body: dict = Body(...), uid: str = Depends(current_uid)) -> dict:
    text = str(body.get("text") or "")
    vectors = knowledge.embed(knowledge.chunk(text)) if text.strip() else None   # fuera de la transacción
    with user_tx(uid) as (cur, tenant):
        try:
            doc = knowledge.add_document(cur, tenant, str(body.get("title") or ""), text, vectors)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        opportunities._audit(cur, tenant, "knowledge_added", doc["id"], {"chunks": doc["chunks"]})
        return doc


@app.delete("/app/knowledge/{document_id}")
def app_delete_knowledge(document_id: UUID, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        if not knowledge.delete_document(cur, tenant, str(document_id)):
            raise HTTPException(status_code=404, detail="Documento no encontrado.")
        opportunities._audit(cur, tenant, "knowledge_deleted", str(document_id), {})
        return {"deleted": True}


@app.get("/app/agent-evals")
def app_eval_cases(uid: str = Depends(current_uid)) -> list[dict]:
    with user_tx(uid) as (cur, tenant):
        return evals.list_cases(cur, tenant)


@app.post("/app/agent-evals")
def app_add_eval_case(body: dict = Body(...), uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        try:
            return evals.add_case(cur, tenant, body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/app/agent-evals/{case_id}")
def app_delete_eval_case(case_id: UUID, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (cur, tenant):
        if not evals.delete_case(cur, tenant, str(case_id)):
            raise HTTPException(status_code=404, detail="Caso no encontrado.")
        return {"deleted": True}


def _draft_profile(cur, tenant: str, draft: dict) -> dict:
    """Perfil vigente con los cambios del borrador aplicados (sin guardarlo)."""
    current = agent_profile._ensure(cur, tenant, _business_name(cur, tenant))
    try:
        return {**current, **agent_profile.validate(draft or {})}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/app/agent-preview")
def app_agent_preview(req: AgentPreview, uid: str = Depends(current_uid)) -> dict:
    """Un mensaje de la vista previa del asistente: el agente responde con el perfil BORRADOR, sin
    guardarlo, en una conversación de prueba (sin pedidos, stock ni cobros) que se borra al reiniciar
    o la limpia el worker."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Escribí un mensaje.")
    with user_tx(uid) as (cur, tenant):
        profile = _draft_profile(cur, tenant, req.profile) if req.profile else None
    try:
        return evals.preview_turn(tenant, req.message, str(req.conversation_id) if req.conversation_id else None,
                                  profile)
    except LookupError:
        raise HTTPException(status_code=404, detail="Vista previa no encontrada.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.delete("/app/agent-preview/{conversation_id}")
def app_agent_preview_end(conversation_id: UUID, uid: str = Depends(current_uid)) -> dict:
    with user_tx(uid) as (_, tenant):
        pass
    return {"deleted": evals.end_preview(tenant, str(conversation_id))}


@app.post("/app/agent-evals/run")
def app_run_evals(body: dict = Body(default={}), uid: str = Depends(current_uid)) -> dict:
    """Corre los casos contra el perfil vigente o contra `profile` (borrador, sin guardar)."""
    with user_tx(uid) as (cur, tenant):
        cases = evals.list_cases(cur, tenant)
        profile = _draft_profile(cur, tenant, body.get("profile")) if body.get("profile") else None
    # Fuera de la transacción del panel: el agente abre las suyas (rol del backend, tenant fijo).
    return evals.run(tenant, cases, profile)
