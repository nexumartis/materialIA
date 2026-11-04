-- Chat en la web del negocio: cómo se ve el botón (lo lee el script en vivo, así el código se pega
-- una sola vez) y en qué sitios se detectó instalado (sólo el dominio; informativo, no es un permiso).

create table if not exists widget_settings (
    tenant_id  uuid primary key references tenants(id) on delete cascade,
    config     jsonb not null default '{}'::jsonb,
    updated_by uuid references auth.users(id) on delete set null,
    updated_at timestamptz not null default now()
);

create table if not exists widget_installs (
    tenant_id  uuid not null references tenants(id) on delete cascade,
    host       text not null check (char_length(host) between 1 and 253),
    first_seen timestamptz not null default now(),
    last_seen  timestamptz not null default now(),
    hits       integer not null default 1,
    primary key (tenant_id, host)
);

alter table widget_settings enable row level security;
alter table widget_installs enable row level security;
revoke all on widget_settings, widget_installs from anon, authenticated;
grant select, insert, update on widget_settings to app_user;
grant select on widget_installs to app_user;
drop policy if exists member_access on widget_settings;
drop policy if exists member_only   on widget_settings;
create policy member_access on widget_settings for all to app_user
    using (tenant_id = (select app_member_tenant())) with check (tenant_id = (select app_member_tenant()));
create policy member_only   on widget_settings as restrictive for all to app_user
    using (tenant_id = (select app_member_tenant())) with check (tenant_id = (select app_member_tenant()));
drop policy if exists member_access on widget_installs;
drop policy if exists member_only   on widget_installs;
create policy member_access on widget_installs for select to app_user using (tenant_id = (select app_member_tenant()));
create policy member_only   on widget_installs as restrictive for all to app_user
    using (tenant_id = (select app_member_tenant()));
