# Cuentas self-serve + aislamiento real por empresa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada negocio cree su cuenta (self-serve), cargue su catálogo, y sus datos queden aislados de verdad por RLS en Postgres.

**Architecture:** Supabase Auth (email+password) emite JWT. FastAPI sigue de gateway: verifica el JWT, resuelve el usuario y, por transacción, hace `SET LOCAL ROLE app_user` (rol sin BYPASSRLS) + `SET LOCAL app.current_uid`; las políticas RLS derivan el tenant del uid vía `memberships`. Una cuenta = un negocio (tenant), provisto por un trigger en el signup.

**Tech Stack:** Postgres/Supabase (migraciones SQL), FastAPI + psycopg, PyJWT, React/Vite + supabase-js.

**Spec:** `docs/superpowers/specs/2026-10-25-cuentas-multitenant-design.md`

## Global Constraints
- Migraciones SQL idempotentes, sin `DROP`/reset remoto; única fuente de verdad del esquema. (verbatim de CLAUDE.md)
- El `tenant_id` lo resuelve el servidor desde el token, **nunca** un parámetro del cliente.
- No romper reglas vigentes: no inventar precios; auditoría sin PII; demo A/B pública intacta.
- El service-role NO se usa en el camino de requests de usuario (solo migraciones/trigger).
- Backend: tests con `pytest` contra Postgres real (Node no aplica). Frontend: sin test runner en el repo → verificación por `tsc && vite build` + captura en navegador (se declara en cada tarea de front).
- Secretos solo en `.env` (nunca commiteados): `SUPABASE_JWT_SECRET`, y en front `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

## Review Focus
- **JWT inválido/expirado/firma mala** → 401 claro, nunca se procede con tenant nulo. (Task 2)
- **Request autenticada SIN membership** (usuario sin tenant) → 403/estado honesto, no fuga ni 500. (Task 2)
- **Fuga entre tenants**: usuario A pide/edita un id de B → RLS no devuelve/no afecta filas de B. (Task 3, Task 4)
- **Falta `Authorization`** en `/app/*` → 401, no cae al tenant demo por defecto. (Task 2)
- **Signup concurrente / email repetido** → un solo tenant por cuenta, sin duplicar; email repetido lo rechaza Supabase Auth. (Task 1)

---

### Task 1: Esquema — memberships, rol `app_user`, RLS por uid, trigger de provisioning

**Files:**
- Create: `supabase/migrations/0003_accounts.sql`
- Test: `backend/tests/test_rls_isolation.py`

**Interfaces:**
- Produces (SQL): rol `app_user` (NOLOGIN, NOBYPASSRLS, GRANTed to postgres); tabla `memberships(user_id uuid, tenant_id uuid, role text, created_at)`; función `handle_new_user()` + trigger `on auth.users insert`; políticas `tenant_isolation_uid` en `opportunities, catalog_items, price_entries, conversations, messages, opportunity_activity, memberships` usando `current_setting('app.current_uid', true)`.
- La política deriva tenant así (verbatim para las tablas con `tenant_id`):
  `tenant_id = (select m.tenant_id from memberships m where m.user_id = nullif(current_setting('app.current_uid', true),'')::uuid)`
  y en `memberships`: `user_id = nullif(current_setting('app.current_uid', true),'')::uuid`.

- [ ] **Step 1: Escribir el test de aislamiento (falla)** en `backend/tests/test_rls_isolation.py`

```python
# Crea dos usuarios+tenants de prueba vía helper SQL (insert directo en auth.users con service-role),
# inserta una oportunidad para cada uno, y verifica el aislamiento bajo app_user.
def test_app_user_sees_only_own_tenant(raw_conn):
    u_a, t_a = _make_account(raw_conn, "a@test.local")
    u_b, t_b = _make_account(raw_conn, "b@test.local")
    _seed_opportunity(raw_conn, t_a); _seed_opportunity(raw_conn, t_b)
    rows_a = _as_user(raw_conn, u_a, "select tenant_id from opportunities")
    assert rows_a and all(str(r["tenant_id"]) == t_a for r in rows_a)

def test_app_user_cannot_write_other_tenant(raw_conn):
    u_a, t_a = _make_account(raw_conn, "a2@test.local")
    _, t_b = _make_account(raw_conn, "b2@test.local")
    # intentar insertar una oportunidad con tenant_id de B bajo la sesión de A -> 0 filas / error RLS
    assert _as_user_write_blocked(raw_conn, u_a, t_b)
```

Helpers del test (en el mismo archivo): `_make_account` inserta en `auth.users` (dispara el trigger → crea tenant+membership, devuelve uid+tenant); `_as_user(conn, uid, sql)` abre tx con `set local role app_user; select set_config('app.current_uid', uid, true);` y corre el sql; `_seed_opportunity` inserta como postgres.

- [ ] **Step 2: Correr y ver que falla**
Run: `cd backend && python -m pytest tests/test_rls_isolation.py -q`
Expected: FAIL (no existe `memberships`/trigger/rol).

- [ ] **Step 3: Escribir la migración** `supabase/migrations/0003_accounts.sql`
Contenido (shape): `create role app_user nologin; grant app_user to postgres;` · `create table if not exists memberships (...)` con FK a `auth.users(id)` y `tenants(id)`, unique(user_id) (una cuenta=un negocio) · `grant select,insert,update,delete on <tablas de negocio> to app_user` (y `usage` en el schema) · `enable row level security` + `create policy tenant_isolation_uid ...` en cada tabla (expresión verbatim de Interfaces) · `create function handle_new_user() returns trigger security definer` que inserta `tenants(name = new.raw_user_meta_data->>'business_name')` y `memberships(new.id, tenant.id, 'owner')` · `create trigger on_auth_user_created after insert on auth.users for each row execute function handle_new_user();`. Idempotente (`if not exists`, `drop policy if exists`).

- [ ] **Step 4: Aplicar y correr tests**
Run: `supabase db reset && cd backend && python -m pytest tests/test_rls_isolation.py -q`
Expected: PASS.

- [ ] **Step 5: Suite completa + commit**
Run: `python -m pytest -q` (sin regresiones: la demo A/B sigue andando como postgres).
Commit: `feat(db): memberships + rol app_user + RLS por uid + trigger de provisioning`

---

### Task 2: Backend — verificación de JWT, `user_tx`, dependencia de auth, `/app/me`

**Files:**
- Modify: `backend/app/config.py` (agregar `supabase_jwt_secret: str = ""`)
- Modify: `backend/app/db.py` (agregar `user_tx`)
- Create: `backend/app/auth.py`
- Modify: `backend/app/main.py` (dependencia + `/app/me`)
- Modify: `backend/pyproject.toml` (dependencia `pyjwt`)
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `db.user_tx(uid: str) -> Iterator[psycopg.Cursor]` (abre tx con `set local role app_user` + `app.current_uid`). `auth.verify_jwt(token: str) -> str` (devuelve el uid/`sub`; lanza `AuthError` si inválido/expirado). `auth.current_uid(authorization: str | None) -> str` (dependencia FastAPI: 401 si falta/!Bearer/ inválido). `auth.resolve_tenant(uid: str) -> str | None` (lee membership bajo `user_tx`; None si no tiene). Endpoint `GET /app/me -> {user_id, tenant_id, business_name}`.

- [ ] **Step 1: Tests (fallan)** en `backend/tests/test_auth.py`

```python
def test_verify_jwt_rejects_bad_signature():
    with pytest.raises(auth.AuthError):
        auth.verify_jwt(_token(sub="u1", secret="otro-secreto"))

def test_verify_jwt_returns_sub():
    assert auth.verify_jwt(_token(sub="u1")) == "u1"

def test_me_requires_bearer():
    assert TestClient(app).get("/app/me").status_code == 401

def test_me_returns_business(raw_conn):
    uid, tid = _make_account(raw_conn, "me@test.local", business_name="Vidriería Té")
    r = TestClient(app).get("/app/me", headers={"authorization": "Bearer " + _token(sub=uid)})
    assert r.status_code == 200 and r.json()["business_name"] == "Vidriería Té"
```

`_token(sub, secret=settings.supabase_jwt_secret)` arma un JWT HS256 con `{"sub":sub,"aud":"authenticated","exp":...}`. En `conftest` setear `settings.supabase_jwt_secret` a un valor de test.

- [ ] **Step 2: Correr y ver fallar**
Run: `cd backend && python -m pytest tests/test_auth.py -q` → FAIL.

- [ ] **Step 3: Implementar**
`pyproject.toml`: agregar `pyjwt`. `config.py`: `supabase_jwt_secret`. `db.user_tx(uid)`: igual a `tenant_tx` pero `cur.execute("set local role app_user"); cur.execute("select set_config('app.current_uid', %s, true)", (uid,))`. `auth.py`: `verify_jwt` con `jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")` → `sub`; `AuthError`; `current_uid` dependencia (parsea `Authorization`); `resolve_tenant(uid)` con `user_tx`. `main.py`: `GET /app/me` usa `Depends(current_uid)` → `resolve_tenant` → datos.

- [ ] **Step 4: Correr y ver pasar**
Run: `python -m pytest tests/test_auth.py -q` → PASS.

- [ ] **Step 5: Commit**
`feat(api): auth con JWT de Supabase, user_tx (RLS) y /app/me`

---

### Task 3: Backend — `/app/opportunities*` autenticados (tenant de la sesión)

**Files:**
- Modify: `backend/app/domain/opportunities.py` (variantes que usan `user_tx`, o parametrizar el tx)
- Modify: `backend/app/main.py` (rutas `/app/opportunities`, `/app/opportunities/{id}` PATCH, `/app/opportunities/{id}/activity`)
- Test: `backend/tests/test_app_opportunities.py`

**Interfaces:**
- Consumes: `auth.current_uid`, `auth.resolve_tenant`, `db.user_tx`.
- Produces: rutas `/app/*` que NO toman `?company`; el tenant sale de la sesión. Reusan la lógica de dominio pero ejecutando bajo `user_tx(uid)` (RLS activo) en vez de `tenant_tx`.
- Decisión del builder: la forma más DRY de reusar el dominio bajo RLS (p. ej. que `opportunities.*` acepten un cursor/tx inyectado, o funciones `*_as_user(uid, ...)`). Mantener `tenant_tx` para `/sandbox`.

- [ ] **Step 1: Tests (fallan)** en `backend/tests/test_app_opportunities.py`

```python
def test_list_scoped_to_session_tenant(raw_conn):
    uid_a, t_a = _make_account(raw_conn, "la@test.local"); _seed_opportunity(raw_conn, t_a)
    _, t_b = _make_account(raw_conn, "lb@test.local"); _seed_opportunity(raw_conn, t_b)
    r = _get("/app/opportunities", uid_a)
    assert r.status_code == 200 and all(o for o in r.json())  # solo de A (no vacío, ninguno de B)

def test_patch_foreign_opportunity_not_found(raw_conn):
    uid_a, _ = _make_account(raw_conn, "pa@test.local")
    opp_b = _seed_opportunity(raw_conn, _make_account(raw_conn, "pb@test.local")[1])
    assert _patch(f"/app/opportunities/{opp_b}", uid_a, {"stage": "cerrada"}).status_code == 404

def test_app_routes_require_auth():
    assert TestClient(app).get("/app/opportunities").status_code == 401
```

- [ ] **Step 2: Correr y ver fallar** → FAIL.
- [ ] **Step 3: Implementar** las rutas `/app/*` (Depends(current_uid)) y el reuso del dominio bajo `user_tx`.
- [ ] **Step 4: Correr y ver pasar** → PASS.
- [ ] **Step 5: Suite completa + commit** `feat(api): /app/opportunities* con tenant de sesión (RLS)`

---

### Task 4: Backend — `/app/catalog` CRUD (autenticado)

**Files:**
- Modify: `backend/app/domain/catalog.py` (create/update/list bajo tenant de sesión)
- Modify: `backend/app/main.py` (`GET/POST/PATCH /app/catalog`)
- Modify: `backend/app/schemas.py` (`CatalogItemInput`, `CatalogItemSummary` si falta)
- Test: `backend/tests/test_app_catalog.py`

**Interfaces:**
- Consumes: `auth.current_uid`, `db.user_tx`.
- Produces: `GET /app/catalog` (productos del tenant), `POST /app/catalog` (alta: sku, name, category, specs, pricing_mode, precio opcional), `PATCH /app/catalog/{id}` (editar/activar). Reusa `import_items` para el alta masiva.

- [ ] **Step 1: Tests (fallan)** en `backend/tests/test_app_catalog.py`

```python
def test_create_and_list_own_products(raw_conn):
    uid, _ = _make_account(raw_conn, "cat@test.local")
    _post("/app/catalog", uid, {"sku":"MAMP-1","name":"Mampara corrediza","category":"mampara","pricing_mode":"custom_quote"})
    items = _get("/app/catalog", uid).json()
    assert any(i["sku"] == "MAMP-1" for i in items)

def test_cannot_see_other_tenant_products(raw_conn):
    uid_a, _ = _make_account(raw_conn, "ca@test.local")
    t_b = _make_account(raw_conn, "cb@test.local")[1]; _seed_product(raw_conn, t_b, "SOLO-B")
    assert all(i["sku"] != "SOLO-B" for i in _get("/app/catalog", uid_a).json())
```

- [ ] **Step 2: Correr y ver fallar** → FAIL.
- [ ] **Step 3: Implementar** el CRUD bajo `user_tx`, upsert por (tenant, sku).
- [ ] **Step 4: Correr y ver pasar** → PASS.
- [ ] **Step 5: Suite completa + commit** `feat(api): /app/catalog CRUD con tenant de sesión`

---

### Task 5: Frontend — Supabase Auth, login/signup, sesión, token en `/app/*`

**Files:**
- Create: `web/src/lib/supabase.ts`, `web/src/lib/session.ts` (hook `useSession`), `web/src/pages/Login.tsx`, `web/src/pages/Signup.tsx`
- Modify: `web/src/lib/api.ts` (base `/app/*` + header `Authorization` del token), `web/src/App.tsx` (guard de sesión + rutas), `web/src/components/Shell.tsx` (reemplazar selector A/B por el negocio logueado + logout), `web/.env.example`
- Modify: `web/package.json` (`@supabase/supabase-js`)

**Interfaces:**
- Consumes: `/app/me`, `/app/opportunities*` (Task 3).
- Produces: sesión global (`useSession() -> {session, user, businessName, loading}`); `api` adjunta `Authorization: Bearer <access_token>`; rutas: sin sesión → `/login`/`/signup`, con sesión → panel. Signup pasa `business_name` en `options.data`.
- Verificación (sin test runner en el repo): `tsc && vite build` + captura en navegador de login, signup y panel logueado.

- [ ] **Step 1: Instalar y configurar** `@supabase/supabase-js`; `supabase.ts` con `VITE_SUPABASE_URL/ANON_KEY`; `.env.example`.
- [ ] **Step 2: `useSession` + guard** en `App.tsx` (loading → login/signup o panel).
- [ ] **Step 3: Login/Signup** (signup con campo "nombre del negocio" → `options: { data: { business_name } }`), estilados con el sistema TasteSkill existente.
- [ ] **Step 4: `api.ts`** apunta a `/app/*` y adjunta el token; `Shell` muestra el negocio + logout; se quita el selector A/B del panel real.
- [ ] **Step 5: Verificar** `cd web && npm run build` (0 errores) + captura navegador (login, signup, panel con el negocio). Ajustar hasta que se vea bien.
- [ ] **Step 6: Commit** `feat(web): login/signup (Supabase Auth) + panel por sesión`

---

### Task 6: Frontend — sección Catálogo (alta/edición de productos)

**Files:**
- Create: `web/src/pages/Catalog.tsx`, `web/src/components/ProductForm.tsx`
- Modify: `web/src/lib/api.ts` (`catalog` GET/POST/PATCH), `web/src/App.tsx` (ruta `#/catalogo`), `web/src/components/Shell.tsx` (ítem de nav "Catálogo")

**Interfaces:**
- Consumes: `/app/catalog` (Task 4), sesión (Task 5).
- Produces: pantalla "Catálogo": tabla de productos del negocio + alta/edición (sku, nombre, categoría, tipo/color/material/medidas en specs, modo de precio, precio si es fijo), con estados vacío/loading/error del sistema existente.
- Verificación: `tsc && vite build` + captura navegador (lista vacía, alta, lista con un producto).

- [ ] **Step 1:** `api.catalog` (list/create/update).
- [ ] **Step 2:** `Catalog.tsx` + `ProductForm.tsx` (TasteSkill), ruta y nav.
- [ ] **Step 3:** Estados vacío/loading/error.
- [ ] **Step 4: Verificar** build + captura navegador (vacío → alta → con producto).
- [ ] **Step 5: Commit** `feat(web): sección Catálogo (alta/edición de productos por negocio)`

---

## Notas de ejecución
- Correr `supabase db reset` tras la migración de Task 1 (aplica 0003 + re-siembra demo A/B).
- El `SUPABASE_JWT_SECRET` local sale de `supabase status` (JWT secret); va en `backend/.env`. En front, `VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY` también de `supabase status`.
- Demo A/B (`/sandbox/*`) y el agente quedan intactos (siguen por `tenant_tx`/canal).
