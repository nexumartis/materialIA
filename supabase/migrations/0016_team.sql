-- 0016 — Equipo: empleados con rol `staff`, invitaciones por email y notas internas en la bandeja.
-- Spec: docs/superpowers/specs/2026-11-02-equipo-roles-design.md. Idempotente y no destructivo:
-- el check de `memberships.role` se reemplaza por uno más amplio (no se borran datos).

-- Roles: owner (dueño, todo) y staff (atiende bandeja, pedidos y oportunidades).
alter table memberships drop constraint if exists memberships_role_check;
alter table memberships add constraint memberships_role_check check (role in ('owner', 'staff'));

-- Invitaciones pendientes. El empleado se registra con ESE email y entra al negocio (sin enviar
-- emails: el dueño le avisa). Un email sólo puede estar invitado a un negocio a la vez.
create table if not exists team_invites (
    email      text primary key check (email = lower(btrim(email)) and email like '%_@_%'),
    tenant_id  uuid not null references tenants(id) on delete cascade,
    role       text not null default 'staff' check (role in ('staff')),
    invited_by uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now()
);
create index if not exists idx_team_invites_tenant on team_invites (tenant_id);
alter table team_invites enable row level security;
revoke all on team_invites from app_user, anon, authenticated;   -- sólo el backend (owner verificado)

-- Provisioning: con invitación y email CONFIRMADO entra como staff al negocio que lo invitó; con
-- invitación sin confirmar no se crea nada hasta confirmar (nadie se apropia del email ajeno);
-- sin invitación, como antes: negocio propio y owner.
create or replace function app_join_invited(p_user uuid, p_email text) returns boolean
    language plpgsql security definer
    set search_path = public, pg_temp
as $$
declare
    v_inv team_invites;
begin
    delete from team_invites where email = lower(btrim(p_email)) returning * into v_inv;
    if v_inv.tenant_id is null then
        return false;
    end if;
    insert into memberships (user_id, tenant_id, role) values (p_user, v_inv.tenant_id, v_inv.role)
        on conflict (user_id) do nothing;
    insert into audit_events (tenant_id, event_type, entity_id, metadata_redacted)
        values (v_inv.tenant_id, 'team_member_joined', p_user, jsonb_build_object('invited_by', v_inv.invited_by));
    return true;
end $$;

create or replace function handle_new_user() returns trigger
    language plpgsql security definer
    set search_path = public, pg_temp
as $$
declare
    v_tenant uuid;
    v_name   text := coalesce(nullif(btrim(new.raw_user_meta_data->>'business_name'), ''), 'Mi negocio');
begin
    if new.email is not null and exists (select 1 from team_invites where email = lower(btrim(new.email))) then
        if new.email_confirmed_at is not null then
            perform app_join_invited(new.id, new.email);
        end if;
        return new;                      -- invitado: nunca se le crea un negocio propio
    end if;
    insert into tenants (name) values (left(v_name, 120)) returning id into v_tenant;
    insert into memberships (user_id, tenant_id, role) values (new.id, v_tenant, 'owner');
    return new;
end $$;

create or replace function handle_user_confirmed() returns trigger
    language plpgsql security definer
    set search_path = public, pg_temp
as $$
begin
    if old.email_confirmed_at is null and new.email_confirmed_at is not null and new.email is not null
       and not exists (select 1 from memberships where user_id = new.id) then
        perform app_join_invited(new.id, new.email);
    end if;
    return new;
end $$;

revoke all on function app_join_invited(uuid, text), handle_new_user(), handle_user_confirmed()
    from public, anon, authenticated;

drop trigger if exists on_auth_user_confirmed on auth.users;
create trigger on_auth_user_confirmed
    after update of email_confirmed_at on auth.users
    for each row execute function handle_user_confirmed();

-- Rol visible para el panel (app_member_tenant ya da el negocio).
create or replace function app_member_role() returns text
    language sql stable security definer
    set search_path = public, pg_temp
as $$ select role from memberships where user_id = app_uid() $$;
revoke all on function app_member_role() from public, anon, authenticated;
grant execute on function app_member_role() to app_user;

-- Notas internas de una conversación: las ve el equipo, nunca el cliente ni el agente.
create table if not exists conversation_notes (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    conversation_id uuid not null references conversations(id) on delete cascade,
    author_id       uuid references auth.users(id) on delete set null,
    author_email    text,
    body            text not null check (char_length(btrim(body)) between 1 and 2000),
    created_at      timestamptz not null default now()
);
create index if not exists idx_conversation_notes_conv on conversation_notes (tenant_id, conversation_id, created_at);
alter table conversation_notes enable row level security;
grant select, insert on conversation_notes to app_user;
drop policy if exists member_access on conversation_notes;
drop policy if exists member_only   on conversation_notes;
create policy member_access on conversation_notes for all to app_user using (tenant_id = app_member_tenant())
    with check (tenant_id = app_member_tenant() and author_id = app_uid());
create policy member_only   on conversation_notes as restrictive for all to app_user using (tenant_id = app_member_tenant())
    with check (tenant_id = app_member_tenant());
