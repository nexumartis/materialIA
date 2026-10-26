-- Agente de ventas — cada negocio arma su agente: perfil del agente, link público y panel con
-- RLS sobre catálogo, stock y pedidos.
-- Diseño: docs/superpowers/specs/2026-10-26-agente-ventas-design.md §11.
-- No destructivo e idempotente.

-- ---------------------------------------------------------------------------
-- Perfil del agente (uno por negocio). FAQ/reglas: lo que el negocio afirma de sí mismo.
-- ---------------------------------------------------------------------------
create table if not exists agent_profiles (
    tenant_id      uuid primary key references tenants(id) on delete cascade,
    business_type  text not null default 'generico',
    public_slug    text not null unique check (public_slug ~ '^[a-z0-9]([a-z0-9-]{1,46}[a-z0-9])$'),
    seller_name    text not null default 'Asistente',
    tone           text not null default 'cercano' check (tone in ('cercano', 'profesional', 'formal')),
    greeting       text not null default '',
    faq            jsonb not null default '[]'::jsonb,    -- [{"q": "...", "a": "..."}]
    rules          jsonb not null default '[]'::jsonb,    -- ["no vendemos sin factura", ...]
    shipping       text not null default '',
    hours          text not null default '',
    payment_methods text not null default '',
    updated_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Grants del panel (app_user, sin BYPASSRLS). Sólo lo que usan las rutas /app/*.
-- ---------------------------------------------------------------------------
grant select, insert, update on agent_profiles   to app_user;
grant select, insert, update on catalog_items    to app_user;
grant select, insert, update on price_entries    to app_user;
grant select, insert, update on stock_levels     to app_user;
grant insert                 on stock_movements  to app_user;
grant select, update         on orders           to app_user;
grant select                 on order_items      to app_user;
grant select                 on payments         to app_user;
revoke all on agent_profiles from anon, authenticated;

alter table agent_profiles enable row level security;

-- Mismo esquema que 0003: permisiva `member_access` + RESTRICTIVA `member_only`, ambas
-- `to app_user`, para que las `tenant_isolation` del sandbox no amplíen su acceso.
do $$
declare t text;
begin
    foreach t in array array['agent_profiles', 'catalog_items', 'price_entries', 'stock_levels',
                             'stock_movements', 'orders', 'order_items', 'payments']
    loop
        execute format('drop policy if exists member_access on %I', t);
        execute format('drop policy if exists member_only on %I', t);
        execute format(
            'create policy member_access on %I for all to app_user '
            'using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant())', t);
        execute format(
            'create policy member_only on %I as restrictive for all to app_user '
            'using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant())', t);
    end loop;
end $$;
