-- Presupuesto Vivo — Cuentas del propietario + aislamiento real por empresa
-- Plan: docs/superpowers/plans/2026-10-26-cuentas-multitenant-v2.md (D1).
-- No destructivo e idempotente: create if not exists / drop ... if exists antes de recrear
-- políticas, funciones y trigger propios. No toca datos existentes.
--
-- Modelo: las requests autenticadas del panel corren con `set local role app_user`
-- (NOBYPASSRLS) + `app.current_uid` = sub del JWT verificado por el backend. El negocio
-- se deriva de `memberships`; el cliente nunca lo elige. El sandbox A/B sigue como antes
-- (rol postgres + app.current_tenant).

-- ---------------------------------------------------------------------------
-- Rol de aplicación sin bypass de RLS. El backend (postgres) lo asume por transacción.
-- ---------------------------------------------------------------------------
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'app_user') then
        create role app_user nologin nobypassrls;
    end if;
end $$;
grant app_user to postgres;
grant usage on schema public to app_user;

-- ---------------------------------------------------------------------------
-- Relación persona ↔ negocio. Este corte: una persona = un negocio (owner).
-- Preparada para varias personas por negocio (varias filas con el mismo tenant_id).
-- ---------------------------------------------------------------------------
create table if not exists memberships (
    user_id    uuid primary key references auth.users(id) on delete cascade,
    tenant_id  uuid not null references tenants(id) on delete cascade,
    role       text not null default 'owner' check (role in ('owner')),
    created_at timestamptz not null default now()
);
create index if not exists idx_memberships_tenant on memberships (tenant_id);

-- ---------------------------------------------------------------------------
-- Helpers de políticas. `app_member_tenant` es security definer para leer memberships
-- sin recursión de RLS; sólo devuelve el negocio del uid fijado por el servidor.
-- ---------------------------------------------------------------------------
create or replace function app_uid() returns uuid
    language sql stable
    set search_path = public, pg_temp
as $$ select nullif(current_setting('app.current_uid', true), '')::uuid $$;

create or replace function app_member_tenant() returns uuid
    language sql stable security definer
    set search_path = public, pg_temp
as $$ select tenant_id from memberships where user_id = app_uid() $$;

-- Supabase da EXECUTE por defecto a anon/authenticated (RPC de PostgREST): se quita.
revoke all on function app_uid(), app_member_tenant() from public, anon, authenticated;
grant execute on function app_uid() to app_user;
grant execute on function app_member_tenant() to app_user;

-- ---------------------------------------------------------------------------
-- Grants mínimos: sólo lo que usan las rutas /app/*. Sin escritura en memberships
-- ni tenants (el alta ocurre únicamente en el trigger de provisioning).
-- ---------------------------------------------------------------------------
revoke all on memberships, tenants, opportunities, opportunity_activity, audit_events from app_user;
grant select         on memberships          to app_user;
grant select         on tenants              to app_user;
grant select, update on opportunities        to app_user;
grant select, insert on opportunity_activity to app_user;
grant insert         on audit_events         to app_user;

-- ---------------------------------------------------------------------------
-- RLS. Para cada tabla: política permisiva `member_access` y política RESTRICTIVA
-- `member_only`, ambas `to app_user`. La restrictiva impide que las permisivas previas
-- (`tenant_isolation`, basadas en app.current_tenant) amplíen el acceso de app_user.
-- ---------------------------------------------------------------------------
alter table memberships  enable row level security;
alter table tenants      enable row level security;
alter table audit_events enable row level security;

drop policy if exists member_access on memberships;
drop policy if exists member_only   on memberships;
create policy member_access on memberships for select to app_user using (user_id = app_uid());
create policy member_only   on memberships as restrictive for all to app_user using (user_id = app_uid());

drop policy if exists member_access on tenants;
drop policy if exists member_only   on tenants;
create policy member_access on tenants for select to app_user using (id = app_member_tenant());
create policy member_only   on tenants as restrictive for all to app_user using (id = app_member_tenant());

-- audit_events/tenants no tenían RLS: el backend (postgres, BYPASSRLS) sigue igual; los
-- roles de PostgREST (anon/authenticated) quedan sin acceso al no tener políticas.
drop policy if exists member_access on audit_events;
drop policy if exists member_only   on audit_events;
create policy member_access on audit_events for insert to app_user
    with check (tenant_id = app_member_tenant());
create policy member_only on audit_events as restrictive for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());

do $$
declare t text;
begin
    foreach t in array array['opportunities', 'opportunity_activity']
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

-- ---------------------------------------------------------------------------
-- Integridad referencial por empresa: la actividad sólo puede colgar de una
-- oportunidad del MISMO negocio (las FK no pasan por RLS).
-- ---------------------------------------------------------------------------
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'opportunities_tenant_id_id_key') then
        alter table opportunities add constraint opportunities_tenant_id_id_key unique (tenant_id, id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'opportunity_activity_tenant_opp_fkey') then
        alter table opportunity_activity add constraint opportunity_activity_tenant_opp_fkey
            foreign key (tenant_id, opportunity_id) references opportunities (tenant_id, id) on delete cascade;
    end if;
end $$;

-- ---------------------------------------------------------------------------
-- Provisioning: al registrarse una persona se crea su negocio y su membresía owner.
-- El nombre llega en raw_user_meta_data.business_name (pedido en el signup).
-- Nota: corre también para altas sin confirmar; con la anon key pública cualquiera puede
-- crear negocios vacíos. Aceptado en este corte (ver plan v2, pendientes).
-- ---------------------------------------------------------------------------
create or replace function handle_new_user() returns trigger
    language plpgsql security definer
    set search_path = public, pg_temp
as $$
declare
    v_tenant uuid;
    v_name   text := coalesce(nullif(btrim(new.raw_user_meta_data->>'business_name'), ''), 'Mi negocio');
begin
    insert into tenants (name) values (left(v_name, 120)) returning id into v_tenant;
    insert into memberships (user_id, tenant_id, role) values (new.id, v_tenant, 'owner');
    return new;
end $$;

revoke all on function handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function handle_new_user();
