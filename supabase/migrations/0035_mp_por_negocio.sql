-- Mercado Pago por negocio: cada comercio conecta SU cuenta (OAuth de Mercado Pago) y cobra en ella.
-- Los tokens se guardan cifrados (Fernet, clave fuera de la base); el panel nunca los ve.
-- El token vence a los 180 días: el worker lo renueva antes con el refresh token (que también cambia).

create table if not exists mp_connections (
    tenant_id               uuid primary key references tenants(id) on delete cascade,
    mp_user_id              text not null check (char_length(mp_user_id) <= 40),
    access_token_encrypted  text not null,
    refresh_token_encrypted text,
    public_key              text check (char_length(public_key) <= 120),
    live_mode               boolean,
    expires_at              timestamptz,
    connected_by            uuid references auth.users(id) on delete set null,
    connected_at            timestamptz not null default now(),
    refreshed_at            timestamptz,
    last_attempt_at         timestamptz,                 -- espaciado de reintentos de renovación
    last_error              text check (char_length(last_error) <= 200)
);
create index if not exists mp_connections_user_idx on mp_connections (mp_user_id);

-- State del OAuth de un solo uso: se crea al pedir el link y se consume en el callback.
create table if not exists mp_oauth_states (
    nonce      text primary key check (char_length(nonce) between 16 and 64),
    tenant_id  uuid not null references tenants(id) on delete cascade,
    created_at timestamptz not null default now()
);
alter table mp_oauth_states enable row level security;
revoke all on mp_oauth_states from anon, authenticated, app_user;

-- Con qué cuenta de Mercado Pago se creó cada link (al reconectar otra cuenta, no se reusa).
alter table payments add column if not exists mp_user_id text;
create index if not exists mp_connections_expiry_idx on mp_connections (expires_at);

alter table mp_connections enable row level security;
revoke all on mp_connections from anon, authenticated, app_user;
-- El panel sólo consulta el estado (sin tokens), y como backend: ninguna política para app_user.
