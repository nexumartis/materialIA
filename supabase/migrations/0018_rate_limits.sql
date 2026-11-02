-- 0018 — Límites de uso: contadores por ventana de tiempo (persona del chat, conversación, negocio,
-- usuario del panel). En Postgres y no en memoria: valen igual con varias instancias del backend.
-- El cubo guarda un hash (no la IP en claro). Sólo lo usa el backend: sin acceso para app_user.
create table if not exists rate_limits (
    bucket       text not null,
    window_start timestamptz not null,
    hits         integer not null default 0,
    primary key (bucket, window_start)
);
create index if not exists idx_rate_limits_window on rate_limits (window_start);
alter table rate_limits enable row level security;
revoke all on rate_limits from app_user, anon, authenticated;
