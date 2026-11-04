-- Campañas: el dueño elige una audiencia (carritos abandonados, pagos pendientes, compradores, etc.),
-- escribe un mensaje con datos reales y la lanza. La audiencia se congela al lanzar (destinatarios),
-- el worker la envía por un canal y se mide quién compró después.
-- En esta fase el único canal habilitado es «simulado»: queda registrado qué se mandaría, no se envía nada.

-- El cliente pide «no me manden más promos» en la charla: aplica aunque todavía no tenga cliente identificado.
alter table conversations add column if not exists marketing_opt_out_at timestamptz;

create table if not exists campaigns (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid not null references tenants(id) on delete cascade,
    name          text not null check (char_length(name) between 1 and 80),
    audience      jsonb not null,
    message       text not null check (char_length(message) between 1 and 700),
    channel       text not null default 'simulado' check (channel in ('simulado', 'whatsapp', 'email')),
    status        text not null default 'draft'
                  check (status in ('draft', 'scheduled', 'sending', 'sent', 'cancelled')),
    scheduled_at  timestamptz,
    started_at    timestamptz,
    sent_at       timestamptz,
    created_by    uuid references auth.users(id) on delete set null,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    unique (tenant_id, id)
);
create index if not exists campaigns_tenant_created_idx on campaigns (tenant_id, created_at desc);
create index if not exists campaigns_due_idx on campaigns (scheduled_at) where status in ('scheduled', 'sending');

create table if not exists campaign_recipients (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid not null references tenants(id) on delete cascade,
    campaign_id      uuid not null,
    conversation_id  uuid not null,
    customer_id      uuid references demo_customers(id) on delete set null,
    order_id         uuid,
    name             text not null,
    detail           text not null default '',
    message          text not null,
    status           text not null default 'pending' check (status in ('pending', 'sent', 'skipped', 'failed')),
    reason           text,
    sent_at          timestamptz,
    created_at       timestamptz not null default now(),
    constraint campaign_recipients_campaign_fkey foreign key (tenant_id, campaign_id)
        references campaigns (tenant_id, id) on delete cascade,
    constraint campaign_recipients_conversation_fkey foreign key (tenant_id, conversation_id)
        references conversations (tenant_id, id) on delete cascade,
    unique (campaign_id, conversation_id)
);
create index if not exists campaign_recipients_pending_idx on campaign_recipients (campaign_id) where status = 'pending';
-- Tope de frecuencia: «¿a esta charla/cliente ya le escribimos esta semana?».
create index if not exists campaign_recipients_conv_sent_idx on campaign_recipients (tenant_id, conversation_id, sent_at desc);
create index if not exists campaign_recipients_cust_sent_idx on campaign_recipients (tenant_id, customer_id, sent_at desc)
    where customer_id is not null;

alter table campaigns           enable row level security;
alter table campaign_recipients enable row level security;
revoke all on campaigns, campaign_recipients from anon, authenticated;
grant select, insert, update on campaigns to app_user;
grant select on campaign_recipients to app_user;
drop policy if exists member_access on campaigns;
drop policy if exists member_only   on campaigns;
create policy member_access on campaigns for all to app_user
    using (tenant_id = (select app_member_tenant())) with check (tenant_id = (select app_member_tenant()));
create policy member_only   on campaigns as restrictive for all to app_user
    using (tenant_id = (select app_member_tenant())) with check (tenant_id = (select app_member_tenant()));
drop policy if exists member_access on campaign_recipients;
drop policy if exists member_only   on campaign_recipients;
create policy member_access on campaign_recipients for select to app_user using (tenant_id = (select app_member_tenant()));
create policy member_only   on campaign_recipients as restrictive for all to app_user
    using (tenant_id = (select app_member_tenant()));
