-- 0027 — Endurecimiento y rendimiento de RLS (auditorías del 04/11/2026).
-- 1) anon y authenticated no usan tablas: el panel va por el backend (rol app_user) y el front sólo
--    usa Supabase Auth. Se revocan sus permisos en las tablas actuales y en las futuras.
-- 2) Las políticas member_access/member_only evaluaban app_member_tenant() en CADA fila (~330x más
--    lento medido con 200k mensajes). Envolverla en (select …) la evalúa una vez por consulta
--    (initPlan). Mismo significado; sólo cambia cuándo se calcula. Idempotente.
revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;

do $$
declare
    p record;
    q text;
    c text;
    rolelist text;
begin
    for p in
        select pp.schemaname, pp.tablename, pp.policyname, pp.permissive, pp.cmd, pp.roles as r, pp.qual, pp.with_check
        from pg_policies pp
        where pp.schemaname = 'public' and pp.policyname in ('member_access', 'member_only')
          and (pp.qual like '%app_member_tenant()%' or pp.with_check like '%app_member_tenant()%')
          and coalesce(pp.qual, '') not like '%SELECT app_member_tenant()%'
    loop
        q := replace(p.qual, 'app_member_tenant()', '(select app_member_tenant())');
        c := replace(p.with_check, 'app_member_tenant()', '(select app_member_tenant())');
        q := replace(q, 'app_uid()', '(select app_uid())');
        c := replace(c, 'app_uid()', '(select app_uid())');
        select string_agg(quote_ident(x), ', ') into rolelist from unnest(p.r) as x;
        execute format('drop policy %I on %I.%I', p.policyname, p.schemaname, p.tablename);
        execute format('create policy %I on %I.%I as %s for %s to %s%s%s',
                       p.policyname, p.schemaname, p.tablename, p.permissive, p.cmd, rolelist,
                       case when q is not null then format(' using (%s)', q) else '' end,
                       case when c is not null then format(' with check (%s)', c) else '' end);
    end loop;
end $$;
