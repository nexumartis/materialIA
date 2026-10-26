> **Documentación vigente:** empezar por [el estado actual](docs/current-state.md) y [la guía para incorporar al socio](docs/ONBOARDING.md).

# materialIA — Agente de ventas

Vendedor por chat que atiende de punta a punta: consulta → **stock y precio reales** →
carrito → pedido → **link de pago** → confirmación **verificada con el proveedor** → estado
del pedido, con el CRM (oportunidades) actualizado. Primer rubro: grifería, sanitarios y
ferretería. Diseño y etapas: [docs/superpowers/specs/2026-10-26-agente-ventas-design.md](docs/superpowers/specs/2026-10-26-agente-ventas-design.md).

> Estado: backend Python/FastAPI + Supabase Postgres, front React (`web/`), cuentas por
> negocio con aislamiento por RLS, stock concurrente, pagos simulados o Mercado Pago de prueba.
> **Sin WhatsApp, sin envíos a clientes reales, sin producción.**

## Arquitectura (resumen)

```
Cliente (chat) → FastAPI → Agente de ventas (interpreta; el backend decide)
   → Herramientas tipadas (tenant fijado en servidor): ofertas, stock, carrito, pedido, pago
   → Supabase Postgres (catálogo, precios, stock, pedidos, pagos, oportunidades, auditoría)
Proveedor de pago → webhook firmado → consulta del pago → pedido PAID (una sola vez)
```

- **Multi-tenant innegociable:** cada query filtra por `tenant_id` resuelto en el servidor;
  el cliente/LLM nunca lo elige. El panel autenticado corre con RLS efectivo (`app_user`).
- **Honestidad:** precios, stock y estados salen siempre de la base o del proveedor; nunca se
  afirma un pago sin confirmación verificable. Lo simulado se rotula como simulado.

## Puesta en marcha

Requisitos: Docker, Supabase CLI, Python 3.12+, Node 20+. Chuleta diaria: [COMO_USAR.md](COMO_USAR.md).

```bash
supabase start && supabase db reset        # migraciones + seed sintético (empresas C y D)

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env                       # defaults: Postgres local, pago simulado
PV_REQUIRE_DB=1 python -m pytest -q        # tests contra Postgres real
uvicorn app.main:app --port 8077 --reload  # Swagger: http://127.0.0.1:8077/docs
python -m app.worker                       # libera reservas de stock vencidas

cd ../web && npm install && npm run dev    # http://localhost:5173/#/venta
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET  | `/health` | Estado, modo del LLM y proveedor de pago (sin secretos). |
| POST | `/sandbox/sales/chat?company=C` | `{message, conversation_id?}` → respuesta, carrito, pedidos, link de pago. |
| GET  | `/sandbox/sales/{conversation_id}?company=C` | Mensajes, carrito y pedidos de la conversación. |
| GET  | `/sandbox/checkout/{preference_id}` | Checkout **simulado** (sólo con `PAYMENT_PROVIDER=simulated`). |
| POST | `/webhooks/{provider}` | Avisos de pago firmados (`simulated` / `mercadopago`). |
| POST | `/sandbox/catalog/import?company=C` | Alta/actualización masiva de catálogo (upsert por sku). |
| GET  | `/app/me`, `/app/opportunities*` | Panel autenticado (JWT de Supabase Auth). |

`company` es un **allowlist fijo** (C/D) mapeado en el servidor a UUIDs del seed; no se confía
un `tenant_id` arbitrario del cliente.

## Supabase de desarrollo REMOTO (opcional)

Proyecto ref `zfmjcturyhxytyfzmcha`: `supabase login` → `supabase link --project-ref
zfmjcturyhxytyfzmcha`. `supabase db push` **modifica el remoto**: revisar las migraciones y
contar con instrucción expresa. `DATABASE_URL` del remoto va sólo en `backend/.env`.

> **Nunca** pongas contraseñas, `service_role` ni credenciales de Mercado Pago en el repo,
> el chat, logs o commits. El `.gitignore` ya excluye `.env`.

## Estructura

```
backend/app/
  main.py            endpoints (sandbox, webhooks, panel /app)
  agent/             sales_agent (planner + herramientas), tools (ToolContext)
  domain/            catalog, inventory (stock), orders (carrito/checkout), opportunities (CRM)
  payments/          providers (simulado / Mercado Pago), service (cobro verificado)
  worker.py          tareas de mantenimiento (reservas vencidas)
supabase/migrations  esquema SQL versionado (única fuente de verdad)
supabase/seed.sql    datos sintéticos de las empresas C (grifería) y D (ferretería)
web/                 front React: agente de ventas, panel de oportunidades, cuentas
```
