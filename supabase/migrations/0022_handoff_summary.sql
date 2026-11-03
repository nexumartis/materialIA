-- 0022 — Resumen al derivar: cuando una conversación queda esperando a una persona, el worker arma
-- un resumen (qué quiere, qué tiene, qué falta) para que el equipo no relea toda la charla. Lo ve el
-- panel (app_user, columnas explícitas como en 0010). Idempotente.
alter table conversations add column if not exists handoff_summary jsonb;
alter table conversations add column if not exists handoff_summary_at timestamptz;
grant select (handoff_summary, handoff_summary_at) on conversations to app_user;
create index if not exists idx_conversations_handoff_pending on conversations (needs_human_at)
    where needs_human_at is not null;

-- Motivo nuevo de derivación: un tema que el negocio configuró para que atienda siempre una persona.
alter table conversations drop constraint if exists conversations_needs_human_reason_check;
alter table conversations add constraint conversations_needs_human_reason_check
    check (needs_human_reason in ('asked', 'quote', 'topic'));
