-- 0013 — Uso de IA por negocio (llamadas y tokens por día y tipo de tarea), para conocer el
-- costo de atender a cada negocio. Lo escribe el backend; el panel sólo lo lee. Idempotente.
create table if not exists llm_usage (
    tenant_id         uuid not null references tenants(id) on delete cascade,
    day               date not null,
    kind              text not null check (kind in ('venta', 'resumen', 'memoria', 'otro')),
    model             text not null,
    calls             integer not null default 0,
    prompt_tokens     bigint not null default 0,
    completion_tokens bigint not null default 0,
    primary key (tenant_id, day, kind, model)
);
alter table llm_usage enable row level security;
drop policy if exists tenant_isolation on llm_usage;
create policy tenant_isolation on llm_usage
    using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid);
drop policy if exists member_access on llm_usage;
create policy member_access on llm_usage for select to app_user using (tenant_id = app_member_tenant());
drop policy if exists member_only on llm_usage;
create policy member_only on llm_usage as restrictive for select to app_user using (tenant_id = app_member_tenant());
revoke all on llm_usage from anon, authenticated, app_user;
grant select on llm_usage to app_user;
