-- Reparto e instalación: el negocio agenda la entrega de un pedido pagado (día, franja, quién va) y
-- el repartidor/instalador la sigue desde su celular. Cada paso (salí, llegué, entregado, no pude)
-- avisa al cliente en su charla y avanza el pedido. El repartidor sólo ve SUS entregas.
-- Idempotente y no destructivo: los checks de rol se reemplazan por unos más amplios.

alter table memberships drop constraint if exists memberships_role_check;
alter table memberships add constraint memberships_role_check check (role in ('owner', 'staff', 'driver'));
alter table team_invites drop constraint if exists team_invites_role_check;
alter table team_invites add constraint team_invites_role_check check (role in ('staff', 'driver'));

create table if not exists delivery_jobs (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    order_id        uuid not null,
    conversation_id uuid,
    kind            text not null default 'delivery' check (kind in ('delivery', 'install', 'delivery_install')),
    scheduled_date  date not null,
    time_window     text not null check (time_window in ('am', 'pm', 'day')),
    assigned_to     uuid references auth.users(id) on delete set null,
    status          text not null default 'scheduled'
                    check (status in ('scheduled', 'on_the_way', 'arrived', 'done', 'failed', 'cancelled')),
    eta_minutes     integer check (eta_minutes between 1 and 600),
    note            text check (char_length(note) <= 300),
    failure_reason  text check (char_length(failure_reason) <= 200),
    started_at      timestamptz,
    arrived_at      timestamptz,
    finished_at     timestamptz,
    created_by      uuid references auth.users(id) on delete set null,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (tenant_id, id),
    constraint delivery_jobs_order_fkey foreign key (tenant_id, order_id)
        references orders (tenant_id, id) on delete cascade
);
-- Una entrega activa por pedido (si falla o se cancela, se puede agendar otra).
create unique index if not exists delivery_jobs_active_order_idx on delivery_jobs (tenant_id, order_id)
    where status not in ('failed', 'cancelled', 'done');
create index if not exists delivery_jobs_day_idx on delivery_jobs (tenant_id, scheduled_date);
create index if not exists delivery_jobs_driver_idx on delivery_jobs (tenant_id, assigned_to, scheduled_date);

alter table delivery_jobs enable row level security;
revoke all on delivery_jobs from anon, authenticated;
grant select, insert, update on delivery_jobs to app_user;
drop policy if exists member_access on delivery_jobs;
drop policy if exists member_only   on delivery_jobs;
create policy member_access on delivery_jobs for all to app_user
    using (tenant_id = (select app_member_tenant())) with check (tenant_id = (select app_member_tenant()));
create policy member_only   on delivery_jobs as restrictive for all to app_user
    using (tenant_id = (select app_member_tenant())) with check (tenant_id = (select app_member_tenant()));
