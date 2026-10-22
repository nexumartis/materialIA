-- Presupuesto Vivo — TAREA 01 — esquema mínimo del MVP
-- Fuente de verdad del esquema: estas migraciones SQL (ruta Supabase CLI).
-- No destructivo, idempotente a nivel objeto (create if not exists).
-- Todas las tablas de negocio llevan tenant_id para aislamiento multiempresa.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Empresas (tenants)
-- ---------------------------------------------------------------------------
create table if not exists tenants (
    id            uuid primary key default gen_random_uuid(),
    name          text not null,
    timezone      text not null default 'America/Argentina/Buenos_Aires',
    currency      text not null default 'ARS',
    settings_json jsonb not null default '{}'::jsonb,
    created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Catálogo por empresa
--   pricing_mode = 'fixed'         -> SKU con precio de lista (price_entries)
--   pricing_mode = 'custom_quote'  -> producto a medida: requiere cotización humana
-- ---------------------------------------------------------------------------
create table if not exists catalog_items (
    id           uuid primary key default gen_random_uuid(),
    tenant_id    uuid not null references tenants(id) on delete cascade,
    sku          text not null,
    name         text not null,
    category     text not null,
    pricing_mode text not null default 'custom_quote'
                 check (pricing_mode in ('fixed', 'custom_quote')),
    specs_json   jsonb not null default '{}'::jsonb,   -- tipo, color, material, ancho_mm, alto_mm...
    active       boolean not null default true,
    currency     text not null default 'ARS',
    updated_at   timestamptz not null default now(),
    unique (tenant_id, sku)
);
create index if not exists idx_catalog_items_tenant on catalog_items (tenant_id);
create index if not exists idx_catalog_items_category on catalog_items (tenant_id, category);

-- ---------------------------------------------------------------------------
-- Precios con vigencia. Un presupuesto emitido debe guardar un snapshot del
-- precio usado (ver opportunities.price_snapshot_json); el catálogo puede cambiar
-- sin mutar retroactivamente lo ya cotizado.
-- ---------------------------------------------------------------------------
create table if not exists price_entries (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references tenants(id) on delete cascade,
    item_id     uuid not null references catalog_items(id) on delete cascade,
    amount      numeric(14,2) not null check (amount >= 0),
    currency    text not null default 'ARS',
    valid_from  date not null default current_date,
    valid_until date,                                  -- null = sin vencimiento
    updated_at  timestamptz not null default now()
);
create index if not exists idx_price_entries_item on price_entries (tenant_id, item_id);

-- ---------------------------------------------------------------------------
-- Clientes ficticios de demostración (nunca datos personales reales)
-- ---------------------------------------------------------------------------
create table if not exists demo_customers (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid not null references tenants(id) on delete cascade,
    display_name   text not null,
    contact_data   jsonb not null default '{}'::jsonb,
    consent_status text not null default 'unknown',
    opt_out_at     timestamptz,
    created_at     timestamptz not null default now()
);
create index if not exists idx_demo_customers_tenant on demo_customers (tenant_id);

-- ---------------------------------------------------------------------------
-- Conversaciones y mensajes (persistir una sesión del simulador web)
-- ---------------------------------------------------------------------------
create table if not exists conversations (
    id                       uuid primary key default gen_random_uuid(),
    tenant_id                uuid not null references tenants(id) on delete cascade,
    customer_id              uuid references demo_customers(id) on delete set null,
    channel                  text not null default 'web_sandbox',
    status                   text not null default 'open',
    last_customer_message_at timestamptz,
    created_at               timestamptz not null default now()
);
create index if not exists idx_conversations_tenant on conversations (tenant_id);

create table if not exists messages (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    conversation_id uuid not null references conversations(id) on delete cascade,
    direction       text not null check (direction in ('inbound', 'outbound')),
    content         text not null,
    created_at      timestamptz not null default now()
);
create index if not exists idx_messages_conv on messages (tenant_id, conversation_id);

-- ---------------------------------------------------------------------------
-- Oportunidades comerciales (el "tablero")
-- ---------------------------------------------------------------------------
create table if not exists opportunities (
    id                   uuid primary key default gen_random_uuid(),
    tenant_id            uuid not null references tenants(id) on delete cascade,
    customer_id          uuid references demo_customers(id) on delete set null,
    conversation_id      uuid references conversations(id) on delete set null,
    requirements_json    jsonb not null default '{}'::jsonb,
    stage                text not null default 'nueva'
                         check (stage in ('nueva','datos_incompletos','para_cotizar','cotizada','seguimiento','cerrada')),
    origin               text not null default 'web_sandbox',
    requires_human_quote boolean not null default true,
    estimated_amount     numeric(14,2),
    price_snapshot_json  jsonb,
    next_action_at       timestamptz,
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);
create index if not exists idx_opportunities_tenant on opportunities (tenant_id);

-- ---------------------------------------------------------------------------
-- Auditoría sin secretos ni datos sensibles
-- ---------------------------------------------------------------------------
create table if not exists audit_events (
    id                uuid primary key default gen_random_uuid(),
    tenant_id         uuid,
    event_type        text not null,
    entity_id         uuid,
    metadata_redacted jsonb not null default '{}'::jsonb,
    created_at        timestamptz not null default now()
);
create index if not exists idx_audit_tenant on audit_events (tenant_id, created_at);

-- ---------------------------------------------------------------------------
-- Row Level Security — defensa en profundidad.
--
-- IMPORTANTE (modelo de aislamiento actual): el backend de TAREA 01 es una API
-- *sólo de servidor* que se conecta con un rol privilegiado (postgres/service_role)
-- que OMITE RLS. Por eso el aislamiento multiempresa REAL y testeado se aplica en
-- la capa de aplicación: cada query filtra por tenant_id resuelto en el servidor,
-- nunca por un parámetro enviado por el cliente (ver backend/app/db.py y tools.py).
--
-- Estas políticas RLS quedan preparadas para cuando se exponga acceso desde un rol
-- restringido / cliente autenticado (p. ej. PostgREST con anon/authenticated o un
-- rol de app sin BYPASSRLS). El backend setea `app.current_tenant` por transacción
-- para que, bajo ese rol, el aislamiento también se cumpla a nivel base de datos.
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
    foreach t in array array['catalog_items','price_entries','demo_customers',
                             'conversations','messages','opportunities']
    loop
        execute format('alter table %I enable row level security', t);
        execute format('drop policy if exists tenant_isolation on %I', t);
        execute format(
            'create policy tenant_isolation on %I using (tenant_id = nullif(current_setting(''app.current_tenant'', true), '''')::uuid)',
            t);
    end loop;
end $$;
