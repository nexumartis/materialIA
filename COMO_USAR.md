# Cómo usar el agente de ventas (chuleta de comandos)

Todo se corre desde la carpeta del proyecto. El backend está en `backend/`.

```bash
cd /Users/tomascastro/materialIA
```

## 1. Prender todo (de cero)

```bash
# Base de datos local (Postgres real, vía Docker)
supabase start
supabase db reset                 # aplica migraciones + seed (empresas C y D)

# Backend
cd backend
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8077   # API en http://127.0.0.1:8077
```

Frontend (React + TypeScript, en `web/`):

```bash
cd web
npm install          # sólo la primera vez
npm run dev          # http://localhost:5173
```

- **Oportunidades:** http://localhost:5173/#/oportunidades
- **Agente de ventas:** http://localhost:5173/#/venta
- **Swagger (API):** http://127.0.0.1:8077/docs
- **Studio (ver la base):** http://127.0.0.1:54323

- **Worker** (libera reservas de stock vencidas): `python -m app.worker` desde `backend/`.

## 2. Apagar

```bash
pkill -f uvicorn        # frena el server
supabase stop           # frena la base (libera RAM); los datos se conservan
```

## 3. Elegir el motor de chat (editar `backend/.env`, luego reiniciar uvicorn)

| Querés… | Poné en `.env` |
|---|---|
| **Rápido + IA de verdad (recomendado)** | `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=https://ollama.com`, `OLLAMA_MODEL=gpt-oss:120b`, `LLM_API_KEY=<tu key de ollama.com>` |
| Gratis sin internet (lento) | `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_MODEL=qwen3:4b` |
| Instantáneo, por reglas (sin IA) | `LLM_PROVIDER=mock` |

> La key de Ollama Cloud se saca en https://ollama.com/settings/keys. `gpt-oss:120b` y
> `gemma4:31b-cloud` son gratis; `minimax-m2.7` es pago. Si da `402`, cambiá a uno gratis.

## 4. Elegir la base de datos (editar `backend/.env`, reiniciar uvicorn)

```bash
# LOCAL (rápida, para demo):
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# CLOUD (compartida, más lenta): guardada en el .env como DATABASE_URL_CLOUD.
# Para activarla, renombrá esa línea a DATABASE_URL= (y comentá/renombrá la local).
```

## 5. Tests

```bash
cd backend && source .venv/bin/activate
python -m pytest -q        # corre siempre en modo mock (determinista)
```

## 6. Supabase cloud (proyecto nexumartis `zfmjcturyhxytyfzmcha`)

```bash
supabase login                                   # autenticar con la cuenta nexumartis
supabase link --project-ref zfmjcturyhxytyfzmcha
supabase db push                                 # aplicar migraciones al cloud
supabase db push --include-seed                  # + cargar datos demo
```

## Reglas de oro
- **Nunca** commitear `.env` (tiene la DB password y la API key). Sólo `.env.example`.
- El **backend** manda en precios/catálogo/oportunidades; el LLM solo interpreta y redacta.
