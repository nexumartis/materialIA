-- Presupuesto Vivo — TAREA 02 — actividad (timeline) de oportunidades
-- El agente y el panel dejan registro de lo que hacen sobre cada oportunidad
-- (creada, cambio de estado, seguimiento). No destructivo e idempotente.
-- No guarda datos personales del cliente: sólo el tipo de acción y un detalle corto.

create table if not exists opportunity_activity (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid not null references tenants(id) on delete cascade,
    opportunity_id uuid not null references opportunities(id) on delete cascade,
    kind           text not null,                       -- creada | cambio_estado | seguimiento | nota
    detail         text not null default '',
    created_at     timestamptz not null default now()
);
create index if not exists idx_opp_activity
    on opportunity_activity (tenant_id, opportunity_id, created_at);

-- RLS (defensa en profundidad, igual que el resto de las tablas de negocio).
alter table opportunity_activity enable row level security;
drop policy if exists tenant_isolation on opportunity_activity;
create policy tenant_isolation on opportunity_activity
    using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid);
