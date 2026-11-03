-- 0023 — Métricas de la bandeja y respuestas rápidas.
-- handoff_events: cada derivación (motivo y hora) y cuándo la respondió una persona; la conversación
-- sólo guarda la derivación vigente, esto guarda la historia para medir tiempos de respuesta.
-- quick_replies: textos que el equipo inserta en la bandeja (los carga el dueño). Idempotente.
create table if not exists handoff_events (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    conversation_id uuid not null references conversations(id) on delete cascade,
    reason          text not null,
    created_at      timestamptz not null default now(),
    answered_at     timestamptz,
    answered_by     uuid references auth.users(id) on delete set null
);
create index if not exists idx_handoff_events_tenant on handoff_events (tenant_id, created_at);
create index if not exists idx_handoff_events_open on handoff_events (tenant_id, conversation_id) where answered_at is null;
alter table handoff_events enable row level security;
grant select, update (answered_at, answered_by) on handoff_events to app_user;
drop policy if exists member_access on handoff_events;
drop policy if exists member_only   on handoff_events;
create policy member_access on handoff_events for all to app_user using (tenant_id = app_member_tenant())
    with check (tenant_id = app_member_tenant());
create policy member_only   on handoff_events as restrictive for all to app_user using (tenant_id = app_member_tenant())
    with check (tenant_id = app_member_tenant());

create table if not exists quick_replies (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid not null references tenants(id) on delete cascade,
    title      text not null check (char_length(btrim(title)) between 1 and 60),
    body       text not null check (char_length(btrim(body)) between 1 and 1000),
    created_at timestamptz not null default now()
);
create index if not exists idx_quick_replies_tenant on quick_replies (tenant_id, title);
alter table quick_replies enable row level security;
grant select on quick_replies to app_user;
drop policy if exists member_access on quick_replies;
drop policy if exists member_only   on quick_replies;
create policy member_access on quick_replies for select to app_user using (tenant_id = app_member_tenant());
create policy member_only   on quick_replies as restrictive for all to app_user using (tenant_id = app_member_tenant());
