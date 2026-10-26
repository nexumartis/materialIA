# Cuentas del propietario + aislamiento real por empresa — Plan v2

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans o subagent-driven-development. Steps con checkbox (`- [ ]`).
> Reemplaza al [plan v1](2026-10-25-cuentas-multitenant.md) (conservado intacto). Incorpora las
> [notas del orquestador](../../reviews/2026-10-25-cuentas-multitenant-notas.md) (puntos 1–5) y reduce el
> alcance a la [decisión aprobada](../../decisions/2026-10-25-cuentas-alcance.md).
> **Estado: propuesta, pendiente de revisión técnica independiente.** No autoriza commits, push, `db push` ni resets remotos.

**Goal:** El propietario de un negocio se registra, inicia y cierra sesión y accede sólo a los datos de su
negocio, con aislamiento garantizado por RLS en Postgres (no sólo por la app).

**Spec:** [`docs/superpowers/specs/2026-10-25-cuentas-multitenant-design.md`](../specs/2026-10-25-cuentas-multitenant-design.md).
Este plan **reemplaza** sus secciones de catálogo (4, slice 4 y la sección Catálogo del front): quedan fuera de alcance.

## Alcance

**Entra:** registro del propietario (email + contraseña + nombre del negocio), login/logout, `/app/me`,
`/app/opportunities` (listar, editar, timeline) bajo sesión, RLS efectivo con rol sin BYPASSRLS, tabla
`memberships` preparada para varias personas por negocio.

**No entra:** catálogo (CRUD/UI), invitaciones, roles más allá de `owner`, gestión de equipo, acceso de una persona
a varios negocios, recuperación de contraseña, canal propio de leads, cambios al chat/agente sandbox,
cualquier cambio en el Supabase remoto.

## Hechos verificados el 26/10/2026 (rama `feat/accounts-multitenant` @ `1e63452`)

- Supabase local (CLI 2.104.0) firma los JWT con **ES256** (JWKS en `/auth/v1/.well-known/jwks.json` devuelve una
  clave EC). El `jwt.decode(..., algorithms=["HS256"])` del v1 **no funcionaría**. Firma del proyecto remoto: **no verificada**.
- Rol `postgres` local: `rolsuper=f`, `rolbypassrls=t`. `authenticated`: sin bypass. El backend conecta como `postgres`.
- Local tiene aplicadas `0001` y `0002`. Remoto: observación previa sin `0002` — **no revalidado** (requiere login).
- `enable_confirmations = false` en `supabase/config.toml` local; el remoto puede diferir.
- Suite actual: `40 passed` contra Postgres local.
- `opportunities.py` abre `tenant_tx` propio en `get_opportunity`, `update_opportunity`, `log_activity`, `audit`;
  `update_opportunity` llama a los otros dos → hoy son transacciones separadas.

## Decisiones técnicas (resuelven las notas 1–5)

### D1 — Grants mínimos por tabla y operación (nota 1)
`app_user` (NOLOGIN, NOBYPASSRLS, `grant app_user to postgres`) recibe **sólo** lo que usan las rutas `/app/*`:

| Tabla | Grant a `app_user` | Política |
|---|---|---|
| `memberships` | `select` | propia fila: `user_id = app_uid()` |
| `tenants` | `select` | `id = app_member_tenant()` |
| `opportunities` | `select, update` | `tenant_id = app_member_tenant()` (using + with check) |
| `opportunity_activity` | `select, insert` | idem |
| `audit_events` | `insert` | `with check (tenant_id = app_member_tenant())`; se habilita RLS en la tabla |

- **Sin `insert/update/delete` sobre `memberships` ni `tenants`**: el alta ocurre sólo en el trigger
  `security definer`. Un usuario no puede cambiarse de empresa ni de rol.
- Sin grants en `catalog_items`, `price_entries`, `conversations`, `messages`, `demo_customers` (no las usa el panel en este corte).
- `app_uid()` = `nullif(current_setting('app.current_uid', true), '')::uuid`.
  `app_member_tenant()` = función `stable security definer` con `search_path` fijo que lee `memberships` para `app_uid()`
  (evita recursión de RLS y la ambigüedad de varias filas: `unique(user_id)` en este corte).
- **Composición con políticas previas:** las `tenant_isolation` de 0001/0002 son permisivas `to public` y usan
  `app.current_tenant`. Para que esa GUC no pueda ampliar el acceso de `app_user` (OR entre permisivas), cada tabla
  recibe además una política **`as restrictive ... to app_user`** con la misma condición de membresía. `user_tx` no setea `app.current_tenant`.

### D2 — Verificación del JWT por JWKS (nota 2)
- `auth.verify_jwt(token) -> uuid`: PyJWT + `PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")` con caché.
  `algorithms` allowlist de asimétricos (`ES256`, `RS256`); valida firma, `exp`, `iss == f"{SUPABASE_URL}/auth/v1"`,
  `aud == "authenticated"`, `sub` UUID válido. Cualquier fallo → `AuthError` → **401**. Nunca HS256 con secreto compartido.
- Config nueva: `supabase_url` (no es secreto). Se elimina `SUPABASE_JWT_SECRET` del plan.
- Antes de desplegar contra el remoto: verificar su JWKS (si el remoto usa sólo secreto legacy HS256, el JWKS vuelve
  vacío y hay que migrar a signing keys en el dashboard; **decisión de los socios**, no del implementador).

### D3 — Una transacción autenticada por request (nota 3)
- `db.user_tx(uid)`: conexión del pool → `set local role app_user` → `set_config('app.current_uid', uid, true)` →
  resuelve `tenant_id` vía `app_member_tenant()` en el mismo cursor → yield `(cur, tenant_id)`. Si no hay membresía → `NoMembership` (→ 403).
- `opportunities.py`: cada operación pasa a una función interna que **recibe `cur`** (`_list(cur, tenant)`,
  `_get(cur, tenant, id)`, `_update(cur, tenant, id, ...)`, `_log_activity(cur, ...)`, `_audit(cur, ...)`). Las funciones
  públicas actuales mantienen su firma y abren `tenant_tx` (sandbox/agente intactos). Las rutas `/app/*` abren un
  único `user_tx` y llaman a las internas → lectura, update, actividad y auditoría en la misma transacción y rol.
- Las queries siguen filtrando `tenant_id` explícito (doble barrera: app + RLS).
- `SET LOCAL` termina con commit/rollback; se prueba que la conexión vuelve al pool sin rol ni uid (ver T3).

### D4 — Pruebas que demuestran aislamiento (nota 4)
- Asserts por **identidad exacta**: conjunto de ids devuelto == ids sembrados de A; ninguno de B; lista no vacía.
- Denegaciones: GET/PATCH/activity de un id de B con sesión de A → 404 y la fila de B **no cambió** (se relee como postgres).
- Casos: sin `Authorization`, `Bearer` mal formado, firma de otra clave, expirado, `iss`/`aud` incorrectos, `sub` no UUID → 401;
  token válido sin membresía → 403.
- SQL directo bajo `app_user`: no puede `update memberships set tenant_id=...`, ni `insert into tenants`, ni leer `tenants` ajeno,
  ni ampliar acceso seteando `app.current_tenant` a B.
- `conftest.py`: con `PV_REQUIRE_DB=1` la falta de Postgres **falla** en vez de saltear. La evidencia de aceptación se
  corre con esa variable y debe mostrar `0 skipped`.

### D5 — Contratos de API y casos del front (nota 5)
- Migran a `/app/*` **sólo** `opportunities`, `patchOpportunity` y `activity` en `api.ts`, con `Authorization: Bearer`.
- Quedan iguales: `/health`, `/sandbox/chat` (página Chat con selector A/B como "probar sin cuenta"), `/sandbox/agent/*`.
- No existe `/app/chat` y no se crea.
- Casos: signup con confirmación activada (mensaje "revisá tu correo", sin sesión), 401 → cerrar sesión y volver a `/login`,
  403 → estado honesto "tu cuenta no tiene negocio asociado", error de red → mensaje existente de `ApiError(0)`.

---

### Task 0: Verificaciones previas (sólo lectura, requiere autorización del usuario)
- [ ] Con la cuenta nexumartis: `supabase migration list --linked` → registrar si el remoto tiene `0002`.
- [ ] `curl <remote>/auth/v1/.well-known/jwks.json` → registrar algoritmo (o vacío).
- [ ] Registrar `enable_confirmations` del remoto (dashboard → Auth).
- [ ] Anotar resultados en `docs/current-state.md`. No aplicar migraciones remotas.

### Task 1: Migración `0003_accounts.sql` + tests SQL de aislamiento
**Files:** Create `supabase/migrations/0003_accounts.sql`, `backend/tests/test_rls_accounts.py`; Modify `backend/tests/conftest.py`.

- [ ] **Step 1 (rojo):** tests con helpers `_make_account(conn, email, business_name)` (insert en `auth.users` como postgres →
  dispara trigger; devuelve `(uid, tenant_id)`), `_as_app_user(conn, uid, sql, params)` (tx con `set local role app_user` +
  `app.current_uid`; rollback al final), `_seed_opportunity(conn, tenant)` → id.
  - signup crea exactamente 1 tenant con `name == business_name` y 1 membership `owner`.
  - `business_name` vacío/ausente → nombre por defecto `'Mi negocio'`, no falla el alta.
  - bajo A: `select id from opportunities` == `{opp_a}`; `select id from tenants` == `{t_a}`.
  - bajo A: `update opportunities ... where id = opp_b` afecta 0 filas; `insert opportunity_activity` con `tenant_id=t_b` → error RLS.
  - bajo A: `update memberships set tenant_id = t_b` → `permission denied`; `insert into tenants` → `permission denied`.
  - bajo A con `set_config('app.current_tenant', t_b, true)`: sigue viendo sólo `{opp_a}`.
  - sin `app.current_uid`: 0 filas en todas las tablas.
  - `conftest`: `PV_REQUIRE_DB=1` → `pytest.fail` en vez de `skip`.
- [ ] **Step 2:** `python -m pytest tests/test_rls_accounts.py -q` → FAIL.
- [ ] **Step 3:** escribir la migración: rol `app_user` (crear sólo si no existe, vía `do $$ ... pg_roles`), `grant app_user to postgres`,
  `grant usage on schema public to app_user`, `memberships(user_id uuid pk-unique → auth.users on delete cascade, tenant_id → tenants on delete cascade, role text check (role in ('owner')) default 'owner', created_at)`,
  funciones `app_uid()` / `app_member_tenant()` (`security definer`, `set search_path = public, pg_temp`), grants de D1,
  `enable row level security` en `memberships`, `tenants`, `audit_events`, políticas permisivas + restrictivas `to app_user`
  (`drop policy if exists` antes de cada `create`), `handle_new_user()` `security definer` + trigger `on_auth_user_created after insert on auth.users`
  (`drop trigger if exists` antes). Revocar `execute` público de `handle_new_user`.
- [ ] **Step 4:** `supabase db reset` (local) → `PV_REQUIRE_DB=1 python -m pytest -q` → todo PASS, 0 skipped, sin regresiones en los 40 existentes.

### Task 2: Auth en FastAPI + `/app/me`
**Files:** Create `backend/app/auth.py`, `backend/tests/test_auth.py`; Modify `backend/app/config.py` (`supabase_url`), `backend/app/db.py` (`user_tx`, `NoMembership`), `backend/app/main.py`, `backend/pyproject.toml` (`pyjwt[crypto]`), `backend/.env.example`.

- [ ] **Step 1 (rojo):** en tests se genera un par EC P-256 y se inyecta el resolvedor de claves (monkeypatch del `PyJWKClient`); `_token(sub, key=..., exp=..., iss=..., aud=...)`.
  - `verify_jwt` acepta token válido y devuelve el `sub`.
  - rechaza: otra clave, expirado, `iss` distinto, `aud` distinto, `sub` no UUID, `alg=HS256`, `alg=none`.
  - `GET /app/me`: sin header → 401; `Basic x` → 401; token válido sin membresía → 403; token de A → `{user_id, tenant_id: t_a, business_name}`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** implementar D2 + `user_tx` de D3 + dependencia `current_uid` + `/app/me` (lee `tenants` bajo `user_tx`).
  CORS: agregar el header `authorization` (ya permitido con `*`); no cambiar orígenes en este corte.
- [ ] **Step 4:** PASS con `PV_REQUIRE_DB=1`.

### Task 3: `/app/opportunities*` en una sola transacción autenticada
**Files:** Modify `backend/app/domain/opportunities.py`, `backend/app/main.py`, `backend/app/db.py` (sólo si hace falta); Create `backend/tests/test_app_opportunities.py`.

- [ ] **Step 1 (rojo):**
  - `GET /app/opportunities` con A → ids == `{opp_a1, opp_a2}`, ninguno de B, no vacío.
  - `PATCH /app/opportunities/{opp_b}` con A → 404; releer `opp_b` como postgres → `stage` y `updated_at` sin cambios; sin actividad nueva en B.
  - `PATCH` de `opp_a` (cambio de estado) → 200, y en `opportunity_activity` hay `cambio_estado` con `tenant_id=t_a`; `audit_events` con `tenant_id=t_a`.
  - `GET /app/opportunities/{opp_b}/activity` con A → lista vacía o 404 (fijar 404 en el contrato).
  - Rollback: si el update falla a mitad (monkeypatch de `_log_activity` que lanza), ni el update ni la actividad persisten.
  - Pool: con `max_size=1` forzado, tras una request `/app/*` que termina en error, un `tenant_tx` posterior ve `current_user = 'postgres'` y `app.current_uid` vacío.
  - Sandbox intacto: los tests existentes de `/sandbox/*` siguen pasando sin cambios.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** refactor de D3 (internas con `cur`, públicas con `tenant_tx`) + rutas `/app/opportunities`, `PATCH /app/opportunities/{id}`, `GET /app/opportunities/{id}/activity` con `Depends(current_uid)` y un único `user_tx`.
- [ ] **Step 4:** PASS completo con `PV_REQUIRE_DB=1`, 0 skipped.

### Task 4: Front — sesión, login/signup, panel por sesión
**Files:** Create `web/src/lib/supabase.ts`, `web/src/lib/session.ts`, `web/src/pages/Login.tsx`, `web/src/pages/Signup.tsx`;
Modify `web/src/lib/api.ts`, `web/src/App.tsx`, `web/src/components/Shell.tsx`, `web/package.json`, `web/.env.example`.

- [ ] **Step 1:** `@supabase/supabase-js`; `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` en `.env.example` (anon es pública; igualmente sólo en `.env`).
- [ ] **Step 2:** `useSession()` (`session`, `business`, `loading`) que llama `/app/me` al iniciar sesión; guard: Oportunidades exige sesión, Chat no.
- [ ] **Step 3:** Login y Signup (signup con "nombre del negocio" en `options.data.business_name`) con el sistema visual existente.
- [ ] **Step 4:** `api.ts` según D5 (sólo tres llamadas migran). Shell: nombre del negocio + "Cerrar sesión" cuando hay sesión; el selector A/B queda sólo en Chat.
- [ ] **Step 5:** manejar los casos de D5 (confirmación, 401, 403, red).
- [ ] **Step 6 — verificación:** `npm run build` sin errores + navegador: signup → panel con nombre del negocio y tablero vacío; logout → `/login`;
  login de nuevo; token vencido/borrado → vuelve a `/login`; Chat A/B sigue funcionando sin sesión. Capturas como evidencia.

### Task 5: Revisión y cierre
- [ ] Revisión del diff completo en contexto fresco (subagente en lectura u otro socio), contra este plan y las invariantes de `CLAUDE.md`.
- [ ] Actualizar `docs/current-state.md` con evidencia (salida de pytest con `0 skipped`, build, capturas) y pendientes.
- [ ] Commits/push/PR sólo con instrucción expresa del usuario.

## Brief (modalidad del socio con Claude Code)
- **Owner de todos los archivos listados:** Tomás (Claude Code). **Revisor:** contexto fresco en lectura; si no está disponible, Mati.
- **Orden:** T0 (puede ir en paralelo) → T1 → T2 → T3 → T4 → T5. Serial: T2 y T3 comparten `db.py` y `main.py`.
- **Skills:** test-driven-development (T1–T3), security-and-hardening (revisión de T1–T2), frontend-ui-engineering (T4), verification-before-completion (T5).
- **Aceptación:** todos los tests de D4 en verde con `PV_REQUIRE_DB=1` y `0 skipped`; ninguna regresión en sandbox/agente; flujo de T4 verificado en navegador;
  revisión sin hallazgos abiertos.

## Preguntas abiertas para los socios
1. ¿Se exige confirmación de correo en el remoto? (cambia el flujo de signup; el código maneja ambos casos).
2. Si el remoto firma con secreto HS256 legacy: ¿migrar a signing keys asimétricas en el dashboard antes de desplegar?
