# Diseño — Cuentas self-serve + aislamiento real por empresa

**Fecha:** 2026-10-25 · **Autor:** agente (decisiones marcadas como "mi llamada") · **Estado:** para aprobación

## Intención y por qué
Hoy Presupuesto Vivo es un sandbox con dos empresas fijas (A/B) y una API que se conecta a
Postgres con un rol privilegiado que **saltea RLS**: el aislamiento multiempresa vive solo en la
capa de aplicación. Para que sea un producto real, cada negocio tiene que **crear su propia cuenta**,
**cargar sus productos**, y que sus datos estén **aislados de verdad** (también a nivel base de datos).
Este diseño cubre ese primer paso: autenticación + tenant por cuenta + RLS efectivo + alta de catálogo.

## Objetivos
- Una persona se registra sola (self-serve) y obtiene su negocio (tenant) propio.
- **Una cuenta = un negocio** (un usuario *owner*, un tenant). Equipos quedan para después.
- Aislamiento real: un usuario **nunca** ve ni toca datos de otro tenant, garantizado por **RLS en Postgres**, no solo por la app.
- El dueño puede **cargar y editar su catálogo** (productos + precios) desde el panel.
- Mantener el backend FastAPI como gateway y la lógica de dominio en Python (sin reescritura a PostgREST).

## No-objetivos (por ahora)
- Equipos / múltiples usuarios por negocio, roles finos.
- Recuperación de contraseña por email en producción (se usa el flujo de Supabase; detalle de config).
- Billing / planes de pago.
- Canal WhatsApp/Telegram (fase aparte).

## Anti-objetivos (sería un fracaso aunque "funcione")
- Que un tenant pueda leer/escribir datos de otro (fuga multiempresa).
- Que el aislamiento dependa de que el cliente mande el `company` correcto.
- Romper el agente, el cotizador determinista o la honestidad (no inventar precios).
- Dejar el service-role en el camino de las requests de usuario.

## Restricciones
- Stack actual: Supabase (Postgres) + FastAPI + React/Vite. Migraciones SQL como única fuente de verdad (sin ORM).
- Reglas innegociables vigentes (tenant del servidor, no inventar precios, auditoría sin PII).
- Node 20/24 local; tests contra Postgres real.

## Decisiones de arquitectura (mi llamada salvo que las corrijas)

### 1. Identidad: Supabase Auth, email + contraseña
Self-serve signup/login con **Supabase Auth** (email + password). Es nativo del stack, maneja el
hash de contraseñas y emite un **JWT** firmado con el secreto del proyecto. (Magic link queda como
opción futura; email+password es lo más familiar y no depende de entrega de mail en la demo.)

### 2. Modelo de datos: tenant + membership
- Se reutiliza la tabla `tenants` (el negocio).
- Nueva tabla `memberships (user_id uuid → auth.users, tenant_id uuid → tenants, role text 'owner', created_at)`.
- **Signup → provisioning atómico:** al crear el usuario se crea su `tenant` y su `membership` (owner).
  Se implementa con un **trigger `on auth.users insert`** (función `SECURITY DEFINER`) que crea el
  tenant y la membership. Así el provisioning es confiable aunque el alta venga del cliente de Supabase.
  El **nombre del negocio se pide en el signup** y viaja en `raw_user_meta_data.business_name`; el
  trigger lo usa como `tenants.name`.

### 3. Aislamiento real: RLS efectivo con un rol que NO saltea RLS
- La FastAPI deja de usar el service-role para las requests de usuario. Usa un **rol de aplicación
  `app_user`** (`NOSUPERUSER`, `NOBYPASSRLS`).
- Por cada request autenticada: verifica el JWT (firma con el secreto del proyecto) → obtiene `auth.uid()`
  → abre transacción y hace `SET LOCAL app.current_uid = '<uid>'`.
- Las **políticas RLS** derivan el tenant del uid vía membership, p. ej.:
  `tenant_id = (select tenant_id from memberships where user_id = current_setting('app.current_uid')::uuid)`.
  `memberships` tiene su propia política (un usuario solo ve su fila). Así **el tenant lo pone el servidor
  desde el token**, nunca un parámetro del cliente, y la DB lo hace cumplir.
- El service-role queda solo para migraciones y el trigger de provisioning (admin), no para requests.

### 4. Catálogo por tenant (alta de productos)
- Sección "Catálogo" en el panel: listar / crear / editar / desactivar productos y sus precios,
  todo scopeado al tenant de la sesión (RLS lo garantiza). Reutiliza el import existente
  (`/catalog/import`) y agrega CRUD mínimo.

### 5. API y endpoints
- Nuevos endpoints autenticados bajo `/app/*` (requieren `Authorization: Bearer <jwt>`):
  `/app/opportunities`, `/app/opportunities/{id}`, `/app/opportunities/{id}/activity`,
  `/app/catalog` (GET/POST/PATCH), `/app/me` (perfil + negocio). El tenant sale de la sesión,
  **ya no hay `?company`**.
- El **chat del cliente** (`/sandbox/chat`) y el **agente** siguen resolviendo tenant por el canal;
  en esta fase se mantienen **solo para la demo pública A/B**.
- La **demo pública A/B se conserva** como "probar sin cuenta" (tenants demo sembrados, acceso sin login).

### 5.b Generación de leads: diferida (decisión del dueño)
En esta fase un negocio nuevo obtiene **panel + catálogo**, pero **todavía no un canal propio** para
recibir consultas: la generación de leads (chat del cliente scopeado a su tenant) llega con la
**fase WhatsApp/Telegram**. Por lo tanto, para un tenant real el tablero de Oportunidades arranca
**vacío** (estado vacío honesto) hasta que exista su canal. *(La carga manual de una oportunidad desde
el panel queda como posible agregado chico posterior, no en este corte.)*

### 6. Frontend
- Pantallas **/login** y **/signup** (Supabase Auth JS). Estado de sesión global; guard de rutas.
- El selector de empresa A/B se reemplaza por el **negocio logueado** (nombre en la barra lateral).
- Nueva sección **Catálogo** para cargar/editar productos.
- El token se adjunta en cada request a `/app/*`.

## Qué queda a criterio del builder
- Forma exacta de verificar el JWT en FastAPI (PyJWT con el secret del proyecto vs. introspección).
- Esquema fino de `memberships` y las políticas RLS por tabla (opportunities, catalog_items, price_entries, conversations, messages, opportunity_activity).
- Detalle del CRUD de catálogo (validaciones, upsert por SKU).
- Diseño visual de login/signup/catálogo (seguir el sistema TasteSkill ya existente).
- Orden de implementación por slices verticales con TDD.

## Plan de entrega (slices, se detalla en el plan)
1. Migración `memberships` + rol `app_user` + políticas RLS + trigger de provisioning. (Con tests de aislamiento.)
2. Auth en FastAPI (verificar JWT, `app.current_uid`, pool con `app_user`) + `/app/me`.
3. `/app/opportunities*` autenticados (tenant de sesión).
4. Catálogo: `/app/catalog` + UI de alta/edición.
5. Front: login/signup, guard, reemplazo del selector A/B.

## Decisiones cerradas (tus respuestas)
- **Generación de leads:** se **difiere a la fase WhatsApp**. Este corte entrega panel + catálogo; el tenant real arranca sin leads hasta tener canal.
- **Demo pública A/B:** se **conserva** como "probar sin cuenta".
- **Nombre del negocio:** se **pide en el signup**.

## Calles que decidí yo (para que las revises al leer)
- Identidad: Supabase Auth con **email + contraseña** (no magic link por ahora).
- Verificación de JWT en FastAPI con el **secreto del proyecto** (PyJWT).
- Rol de DB **`app_user`** (`NOBYPASSRLS`) para las requests; service-role solo para migraciones/trigger.
- El backend setea `app.current_uid` desde el token; el tenant se deriva por RLS vía `memberships`.
- Se mantiene FastAPI como gateway (no se migra a PostgREST).
