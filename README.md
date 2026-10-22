# Presupuesto Vivo — MVP (corte vertical, TAREA 01)

Convierte consultas de compra en **solicitudes de cotización calificadas** y
**oportunidades comerciales trazables**, con **cotización controlada** y **aprobación
humana** cuando corresponde. No es un bot genérico de WhatsApp: el valor está en el
flujo de negocio, las reglas y los datos gobernados. El LLM y el canal son intercambiables.

> Estado: **Fase 1** — backend Python + Supabase Postgres, catálogo por empresa, chat
> sandbox que crea una oportunidad, motor de precios determinista y tests. **Sin WhatsApp,
> sin envíos a clientes, sin producción.**

## Arquitectura (resumen)

```
Cliente (web sandbox) → FastAPI → Orquestador (LLM/mock interpreta, el backend decide)
   → Tools tipadas (tenant fijado en servidor) → Supabase Postgres (catálogo, precios,
     oportunidades, mensajes, auditoría)
   → Cotizador determinista (no inventa precios; a medida ⇒ requires_human)
```

- **Multi-tenant innegociable:** cada query filtra por `tenant_id` resuelto en el
  servidor; el cliente/LLM nunca lo elige. RLS queda preparada como defensa en profundidad
  (ver `supabase/migrations/0001_init.sql`).
- **Honestidad:** sin API key el backend corre en **modo MOCK explícito** (`mode:"mock"`),
  no finge ser un modelo real. Nunca afirma precios/stock no verificados.

## Requisitos

- Docker (corriendo), Supabase CLI, Python 3.12+.

## Puesta en marcha — macOS / Linux

```bash
# 1) Base de datos local (Postgres real de Supabase)
supabase start
supabase db reset          # aplica migraciones + seed (datos sintéticos A/B)

# 2) Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .           # o: pip install -r requirements (ver pyproject)
cp .env.example .env        # defaults ya apuntan al Postgres local

# 3) Tests (contra Postgres real)
python -m pytest -q

# 4) Servidor
uvicorn app.main:app --port 8077 --reload
# Swagger: http://127.0.0.1:8077/docs   ·  UI mínima: abrir ../sandbox_ui.html
```

## Puesta en marcha — Windows PowerShell

```powershell
supabase start
supabase db reset

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env

python -m pytest -q
uvicorn app.main:app --port 8077 --reload
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET  | `/health` | Estado y modo de conexión (sin secretos). |
| GET  | `/sandbox/products?company=A` | Catálogo autorizado de la empresa demo. |
| POST | `/sandbox/chat?company=A` | `{message, conversation_id?}` → respuesta + oportunidad. |
| GET  | `/sandbox/opportunities?company=A` | Oportunidades de la empresa. |

`company` es un **allowlist fijo** (A/B) mapeado en el servidor a UUIDs del seed; no se
confía un `tenant_id` arbitrario del cliente.

Ejemplo:

```bash
curl -s -X POST "http://127.0.0.1:8077/sandbox/chat?company=A" \
  -H 'content-type: application/json' \
  -d '{"message":"Quiero una mampara corrediza negra de 1,60 x 1,90 en Tigre"}'
```

## Conectar un Supabase de desarrollo REMOTO (opcional)

El proyecto corre contra **Supabase local** por defecto. Para apuntar a un proyecto cloud
de desarrollo (ref `zfmjcturyhxytyfzmcha`):

```bash
# Autenticá el CLI con la cuenta dueña del proyecto (abre el navegador):
supabase login
# Enlazá el proyecto (pide la DB password; NO se commitea):
supabase link --project-ref zfmjcturyhxytyfzmcha
# Aplicá las migraciones al remoto (revisá el diff antes):
supabase db push
# Para que el backend use el remoto, seteá DATABASE_URL en backend/.env
# (connection string del dashboard; la clave vive sólo en .env, nunca en git).
```

> **Nunca** pongas contraseñas ni `service_role` keys en el repo, el chat, logs o commits.
> El `.gitignore` ya excluye `.env` y claves.

## Habilitar el LLM real

Por defecto, modo mock. Para usar un modelo económico por API (ej. `gpt-6-luna`):

```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-...        # sólo en entorno/secreto, nunca en git
export LLM_MODEL=gpt-6-luna
```

El backend sigue ejecutando las herramientas y decidiendo; el modelo sólo interpreta y redacta.

## Estructura

```
backend/            FastAPI + dominio + agente + tests
  app/
    main.py         endpoints sandbox
    config.py       settings por entorno
    db.py           conexión Postgres + tenant_tx (RLS GUC)
    domain/         catalog, pricing (determinista), opportunities
    agent/          orchestrator, tools (tenant-safe), llm_adapter, skills/*.yaml
  tests/            catálogo, aislamiento multi-tenant, chat (8 escenarios)
supabase/
  migrations/0001_init.sql   esquema mínimo + RLS preparada
  seed.sql                   datos sintéticos de 2 empresas A/B
sandbox_ui.html     UI mínima opcional contra la API local
docs/TAREA01_REPORTE.md      reporte de ejecución
```
