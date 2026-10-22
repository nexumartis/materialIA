# CLAUDE.md — Presupuesto Vivo

Guía para agentes que trabajen en este repo. Leer junto con `docs/TAREA01_REPORTE.md`.

## Qué es
MVP (Fase 1) que convierte consultas de compra en **oportunidades trazables** con
**cotización controlada** y **aprobación humana**. Backend Python/FastAPI + Supabase Postgres.
Nicho inicial: mamparas/cerramientos a medida (AR). **Datos del seed = sintéticos.**

## Correr en local
```bash
supabase start && supabase db reset          # Postgres real + migraciones + seed A/B
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e .
cp .env.example .env
python -m pytest -q                          # 13 tests contra Postgres real
uvicorn app.main:app --port 8077 --reload    # /docs para Swagger
```

## Reglas innegociables (no romper)
- **Multi-tenant:** el `tenant_id` lo resuelve el servidor (`ToolContext`, allowlist A/B en
  `main.py`); **nunca** se confía un tenant del cliente/LLM. Toda query filtra por tenant.
- **Honestidad:** no inventar precios, stock ni medidas. `custom_quote`/precio vencido/sin
  precio ⇒ `requires_human`. Sin API key ⇒ `mode:"mock"` explícito, nunca fingir modelo real.
- **Secretos:** jamás commitear `.env`, DB passwords ni `service_role`. Sólo `.env.example`.
- **Esquema:** una sola fuente de verdad = migraciones SQL en `supabase/migrations/`. No ORM.
  Migraciones idempotentes, sin `DROP`/reset remoto sin permiso.
- **Alcance:** NO WhatsApp, NO envíos a clientes, NO producción en esta fase.

## Mapa
- `backend/app/domain/` — catálogo, `pricing.py` (determinista), oportunidades.
- `backend/app/agent/` — `orchestrator.py` (el backend decide), `tools.py` (tenant-safe),
  `llm_adapter.py` (mock/openai), `skills/*.yaml` (versionadas).
- `supabase/migrations/0001_init.sql` — esquema + RLS preparada (defensa en profundidad).
- `backend/tests/` — 8 escenarios del Paso E.

## Supabase remoto (dev)
Proyecto ref `zfmjcturyhxytyfzmcha` (cuenta nexumartis). Para enlazar: `supabase login` con esa
cuenta → `supabase link --project-ref zfmjcturyhxytyfzmcha` → `supabase db push`. `DATABASE_URL`
del remoto va en `backend/.env` (no en git).
