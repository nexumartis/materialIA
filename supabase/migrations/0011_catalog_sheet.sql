-- 0011 — Google Sheets como catálogo vivo.
--
-- Cada negocio puede conectar UNA planilla pública (exportación CSV de una pestaña) que se
-- sincroniza con el catálogo. `catalog_items.sheet_stock` guarda el último stock leído de la
-- planilla: sólo un cambio en ese número se aplica como stock físico, así una sincronización no
-- borra lo vendido por el agente. Idempotente; sin DROP de datos.

create table if not exists catalog_sources (
    tenant_id      uuid primary key references tenants(id) on delete cascade,
    kind           text not null default 'google_sheet' check (kind in ('google_sheet')),
    sheet_id       text not null check (sheet_id ~ '^[A-Za-z0-9_-]{20,120}$'),
    published      boolean not null default false,   -- link de «Publicar en la web» (/d/e/2PACX-…)
    gid            text not null default '0' check (gid ~ '^[0-9]{1,12}$'),
    enabled        boolean not null default true,
    last_synced_at timestamptz,
    last_status    text check (last_status in ('ok', 'error')),
    last_result    jsonb,          -- {created, updated, errors[], missing}
    last_error     text,
    created_by     uuid references auth.users(id) on delete set null,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index if not exists idx_catalog_sources_due on catalog_sources (last_synced_at) where enabled;

alter table catalog_items add column if not exists sheet_stock integer;

-- RLS: backend (tenant_isolation) y panel (member_access + RESTRICTIVA member_only), como 0005.
alter table catalog_sources enable row level security;
drop policy if exists tenant_isolation on catalog_sources;
create policy tenant_isolation on catalog_sources
    using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid);
drop policy if exists member_access on catalog_sources;
create policy member_access on catalog_sources for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
drop policy if exists member_only on catalog_sources;
create policy member_only on catalog_sources as restrictive for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
revoke all on catalog_sources from anon, authenticated;
grant select, insert, update, delete on catalog_sources to app_user;
