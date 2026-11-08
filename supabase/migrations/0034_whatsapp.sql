-- 0034 — WhatsApp (Cloud API de Meta), etapa 1.
-- Diseño: docs/superpowers/specs/2026-11-08-whatsapp-design.md.
-- * whatsapp_connections: el número de cada negocio. El negocio de un aviso de Meta sale SÓLO de acá
--   (por phone_number_id). El token va cifrado por el backend; ningún rol del panel lee esta tabla.
-- * conversations.wa_id: una conversación por contacto de WhatsApp y negocio.
-- * whatsapp_inbound: cada mensaje de Meta se procesa una sola vez (Meta reintenta los avisos).
-- * whatsapp_outbox: cola de salida. La llena un trigger con TODO mensaje saliente de una conversación
--   de WhatsApp (agente, bandeja, avisos de pago, reparto, envío), menos lo que el dueño escribió desde
--   la app (payload.type = 'owner_app', etapa 3). La vacía el backend con reintentos.
-- Idempotente, sin operaciones destructivas sobre datos.

create table if not exists whatsapp_connections (
    tenant_id        uuid primary key references tenants(id) on delete cascade,
    phone_number_id  text not null unique,
    waba_id          text not null,
    display_phone    text not null,
    token_encrypted  text not null,
    status           text not null default 'connected' check (status in ('connected', 'disconnected')),
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
);

alter table conversations add column if not exists wa_id text;
create unique index if not exists uq_conversations_wa_id on conversations (tenant_id, wa_id) where wa_id is not null;

create table if not exists whatsapp_inbound (
    wamid        text primary key,
    tenant_id    uuid not null references tenants(id) on delete cascade,
    received_at  timestamptz not null default now()
);
-- El mensaje se guarda hasta procesarlo: si el proceso falla o se reinicia, el worker lo retoma
-- (hasta 3 intentos). processed_at null = todavía no se atendió.
alter table whatsapp_inbound add column if not exists message jsonb;
alter table whatsapp_inbound add column if not exists processed_at timestamptz;
alter table whatsapp_inbound add column if not exists attempts integer not null default 0;
create index if not exists idx_whatsapp_inbound_pending on whatsapp_inbound (received_at) where processed_at is null;

create table if not exists whatsapp_outbox (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid not null references tenants(id) on delete cascade,
    conversation_id  uuid not null references conversations(id) on delete cascade,
    message_id       uuid not null unique references messages(id) on delete cascade,
    status           text not null default 'pending' check (status in ('pending', 'sent', 'failed', 'window_closed')),
    attempts         integer not null default 0,
    next_attempt_at  timestamptz not null default now(),
    wamid            text,
    last_error       text,
    created_at       timestamptz not null default now(),
    sent_at          timestamptz
);
create index if not exists idx_whatsapp_outbox_due on whatsapp_outbox (next_attempt_at) where status = 'pending';
create index if not exists idx_whatsapp_outbox_wamid on whatsapp_outbox (wamid) where wamid is not null;

alter table whatsapp_connections enable row level security;
alter table whatsapp_inbound     enable row level security;
alter table whatsapp_outbox      enable row level security;
revoke all on whatsapp_connections, whatsapp_inbound, whatsapp_outbox from anon, authenticated, app_user;

create or replace function app_enqueue_whatsapp() returns trigger
    language plpgsql security definer
    set search_path = public, pg_temp
as $$
begin
    if new.direction = 'outbound'
       and coalesce(new.payload->>'type', '') <> 'owner_app'
       and exists (select 1 from conversations c
                   where c.tenant_id = new.tenant_id and c.id = new.conversation_id and c.wa_id is not null) then
        insert into whatsapp_outbox (tenant_id, conversation_id, message_id)
        values (new.tenant_id, new.conversation_id, new.id);
    end if;
    return new;
end $$;
revoke all on function app_enqueue_whatsapp() from public, anon, authenticated;

drop trigger if exists trg_messages_whatsapp_outbox on messages;
create trigger trg_messages_whatsapp_outbox after insert on messages
    for each row execute function app_enqueue_whatsapp();
