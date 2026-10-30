-- 0010 — Bandeja de conversaciones y toma de control humana (roadmap etapa 2).
--
-- El dueño ve las conversaciones de su negocio, toma el control (el agente se pausa en esa
-- conversación), responde como persona y la devuelve al agente. Idempotente; sin DROP de datos.

alter table conversations add column if not exists needs_human_at timestamptz;   -- derivada desde
-- Por qué: 'asked' = el cliente pidió una persona; 'quote' = a medida, sin precio o precio vencido.
alter table conversations add column if not exists needs_human_reason text
    check (needs_human_reason in ('asked', 'quote'));
alter table conversations add column if not exists taken_by uuid references auth.users(id) on delete set null;
alter table conversations add column if not exists taken_at timestamptz;
create index if not exists idx_conversations_needs_human
    on conversations (tenant_id, needs_human_at) where needs_human_at is not null;
create index if not exists idx_messages_conversation_created on messages (tenant_id, conversation_id, created_at);

-- Panel (app_user): mismo esquema que 0003/0005, permisiva member_access + RESTRICTIVA member_only.
do $$
declare t text;
begin
    foreach t in array array['conversations', 'messages']
    loop
        execute format('drop policy if exists member_access on %I', t);
        execute format('drop policy if exists member_only on %I', t);
        execute format(
            'create policy member_access on %I for all to app_user '
            'using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant())', t);
        execute format(
            'create policy member_only on %I as restrictive for all to app_user '
            'using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant())', t);
    end loop;
end $$;

-- Lectura de conversaciones POR COLUMNAS: el panel no ve el hash del token del comprador ni el
-- estado interno del agente. Escritura sólo de la toma de control.
revoke all on conversations, messages from app_user;
grant select (id, tenant_id, customer_id, channel, status, last_customer_message_at, created_at,
              needs_human_at, needs_human_reason, taken_by, taken_at) on conversations to app_user;
grant update (needs_human_at, needs_human_reason, taken_by, taken_at) on conversations to app_user;
grant select, insert on messages to app_user;
