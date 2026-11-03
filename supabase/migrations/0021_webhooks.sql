-- 0021 — Webhooks salientes: el negocio registra un endpoint HTTPS y recibe eventos firmados
-- (HMAC-SHA256) de pedidos, derivaciones y calificaciones. Patrón outbox: el evento se guarda en
-- la MISMA transacción que el cambio y lo entrega el worker con reintentos. El secreto sólo lo lee
-- el backend (sin acceso para app_user). Idempotente.
create table if not exists webhook_endpoints (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    url             text not null check (url like 'https://%' and char_length(url) <= 500),
    secret          text not null,
    events          text[] not null,
    active          boolean not null default true,
    created_by      uuid references auth.users(id) on delete set null,
    created_at      timestamptz not null default now(),
    last_success_at timestamptz,
    last_error      text,
    unique (tenant_id, id)
);
create index if not exists idx_webhook_endpoints_tenant on webhook_endpoints (tenant_id);

create table if not exists webhook_deliveries (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid not null references tenants(id) on delete cascade,
    endpoint_id      uuid not null,
    event            text not null,
    payload          jsonb not null,
    status           text not null default 'pending' check (status in ('pending', 'sent', 'failed')),
    attempts         integer not null default 0,
    next_attempt_at  timestamptz not null default now(),
    last_status_code integer,
    last_error       text,
    created_at       timestamptz not null default now(),
    sent_at          timestamptz,
    constraint webhook_deliveries_endpoint_fkey foreign key (tenant_id, endpoint_id)
        references webhook_endpoints (tenant_id, id) on delete cascade
);
create index if not exists idx_webhook_deliveries_due on webhook_deliveries (next_attempt_at) where status = 'pending';
create index if not exists idx_webhook_deliveries_tenant on webhook_deliveries (tenant_id, created_at desc);

alter table webhook_endpoints  enable row level security;
alter table webhook_deliveries enable row level security;
revoke all on webhook_endpoints, webhook_deliveries from app_user, anon, authenticated;
-- El panel (rol app_user) también encola: p. ej. el dueño cancela un pedido. Sólo ve de los
-- endpoints lo necesario para encolar (NUNCA el secreto) e inserta envíos de SU negocio.
grant select (id, tenant_id, events, active) on webhook_endpoints to app_user;
grant insert on webhook_deliveries to app_user;
drop policy if exists member_access on webhook_endpoints;
drop policy if exists member_only   on webhook_endpoints;
create policy member_access on webhook_endpoints for select to app_user using (tenant_id = app_member_tenant());
create policy member_only   on webhook_endpoints as restrictive for all to app_user using (tenant_id = app_member_tenant());
drop policy if exists member_access on webhook_deliveries;
drop policy if exists member_only   on webhook_deliveries;
create policy member_access on webhook_deliveries for insert to app_user with check (tenant_id = app_member_tenant());
create policy member_only   on webhook_deliveries as restrictive for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
