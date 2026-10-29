# CLAUDE.md — Presupuesto Vivo

**Primera lectura en cada tarea:** [docs/current-state.md](docs/current-state.md).
Después seguir el acuerdo compartido de [AGENTS.md](AGENTS.md) y, según la tarea,
[docs/AI-WORKFLOW.md](docs/AI-WORKFLOW.md). Las invariantes de este archivo aplican a todos los agentes.
Para preparar el entorno del socio que sólo usa Claude Code, seguir [docs/ONBOARDING.md](docs/ONBOARDING.md).
`docs/TAREA01_REPORTE.md` conserva evidencia histórica de TAREA 01; sus conteos y resultados no son validación actual.

## Qué es
Agente de ventas por chat de punta a punta: stock y precio reales, carrito, pedido, link de
pago y confirmación verificada con el proveedor, con el CRM (oportunidades) actualizado.
Backend Python/FastAPI + Supabase Postgres, front React. Primer rubro: grifería/sanitarios/
ferretería (AR). Lo a medida (`custom_quote`) va a una persona. **Datos del seed = sintéticos.**

## Correr en local
```bash
supabase start && supabase db reset          # Postgres real + migraciones + seed C/D
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e .
cp .env.example .env
python -m pytest -q                          # tests contra Postgres real; registrar resultado actual
uvicorn app.main:app --port 8077 --reload    # /docs para Swagger
```

## Reglas innegociables (no romper)
- **Multi-tenant:** el `tenant_id` lo resuelve el servidor (`ToolContext`, allowlist C/D en
  `main.py`, membresía en el panel); **nunca** se confía un tenant del cliente/LLM. Toda query filtra por tenant.
- **Honestidad:** no inventar precios, stock ni medidas. `custom_quote`/precio vencido/sin
  precio ⇒ `requires_human`. Un pedido es pagado sólo con el pago verificado del proveedor o con una
  transferencia que el dueño cotejó en su banco (`confirm_transfer`, auditada). Un comprobante o su
  OCR nunca acreditan un pago.
  Sin LLM ⇒ `mode:"mock"` explícito, nunca fingir modelo real.
- **Secretos:** jamás commitear `.env`, DB passwords ni `service_role`. Sólo `.env.example`.
- **Esquema:** una sola fuente de verdad = migraciones SQL en `supabase/migrations/`. No ORM.
  Migraciones idempotentes, sin `DROP`/reset remoto sin permiso.
- **Alcance:** NO WhatsApp, NO envíos a clientes, NO producción en esta fase.

## Mapa
- `backend/app/domain/` — catálogo, `inventory.py` (stock concurrente), `orders.py`
  (carrito/checkout), oportunidades (CRM).
- `backend/app/agent/` — `sales_agent.py` (planner + herramientas), `tools.py` (`ToolContext`).
- `backend/app/payments/` — proveedores (simulado / Mercado Pago) y cobro verificado.
- `supabase/migrations/` — esquema SQL y políticas de aislamiento versionados.
- `backend/tests/` — pruebas; verificar el conjunto y los resultados vigentes.

## Supabase remoto (dev)
Proyecto ref `zfmjcturyhxytyfzmcha` (cuenta nexumartis). Para enlazar: `supabase login` con esa
cuenta → `supabase link --project-ref zfmjcturyhxytyfzmcha`. Un `supabase db push` modifica
el remoto: revisar las migraciones y contar con instrucción expresa para aplicarlas. `DATABASE_URL`
del remoto va en `backend/.env` (no en git).
