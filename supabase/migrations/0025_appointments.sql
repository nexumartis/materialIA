-- 0025 — Turnos: el cliente reserva en el chat un horario libre de un servicio que configuró el
-- negocio (retiro, medición, instalación, probador). El cupo se respeta con un bloqueo por negocio.
-- El panel ve y cancela los del negocio (RLS). Idempotente.
create table if not exists appointments (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    conversation_id uuid references conversations(id) on delete set null,
    service         text not null check (char_length(service) between 1 and 60),
    starts_at       timestamptz not null,
    ends_at         timestamptz not null check (ends_at > starts_at),
    status          text not null default 'booked' check (status in ('booked', 'cancelled')),
    created_at      timestamptz not null default now(),
    cancelled_at    timestamptz,
    cancelled_by    uuid references auth.users(id) on delete set null
);
create index if not exists idx_appointments_tenant_time on appointments (tenant_id, starts_at) where status = 'booked';
alter table appointments enable row level security;
grant select, update (status, cancelled_at, cancelled_by) on appointments to app_user;
drop policy if exists member_access on appointments;
drop policy if exists member_only   on appointments;
create policy member_access on appointments for all to app_user using (tenant_id = app_member_tenant())
    with check (tenant_id = app_member_tenant());
create policy member_only   on appointments as restrictive for all to app_user using (tenant_id = app_member_tenant())
    with check (tenant_id = app_member_tenant());
