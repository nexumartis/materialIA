-- 0024 — Privacidad: bloquear un contacto (pausa el agente en esa conversación y en las del mismo
-- cliente recordado) y registro de datos sensibles ocultados. Idempotente.
alter table conversations add column if not exists blocked_at timestamptz;
alter table conversations add column if not exists blocked_by uuid references auth.users(id) on delete set null;
alter table conversations add column if not exists redacted_at timestamptz;
grant select (blocked_at, redacted_at) on conversations to app_user;
