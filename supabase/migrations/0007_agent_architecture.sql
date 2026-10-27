-- Arquitectura del agente por negocio: versiones del perfil, políticas aplicadas por código,
-- herramientas por negocio, memoria del cliente, base de conocimiento (búsqueda de texto + vectores)
-- y evaluaciones. Investigación: docs/research/2026-10-27-arquitectura-agentes-personalizados.md.
-- No destructivo e idempotente.

-- pgvector: en Supabase vive en `extensions`; si ya estaba instalado en otro esquema, se usa ése.
create extension if not exists vector with schema extensions;

-- ---------------------------------------------------------------------------
-- 1. Versiones del perfil. Cada "Guardar" crea una versión inmutable; el perfil vigente apunta a
--    la suya y cada respuesta del agente registra con qué versión se generó.
-- ---------------------------------------------------------------------------
alter table agent_profiles add column if not exists version integer not null default 1;
-- 2. Políticas que hace cumplir el CÓDIGO (no el modelo) y herramientas apagadas por el negocio.
alter table agent_profiles add column if not exists policies jsonb not null default '{}'::jsonb;
alter table agent_profiles add column if not exists disabled_tools jsonb not null default '[]'::jsonb;

create table if not exists agent_profile_versions (
    tenant_id  uuid not null references tenants(id) on delete cascade,
    version    integer not null check (version > 0),
    content    jsonb not null,
    created_by uuid,
    created_at timestamptz not null default now(),
    primary key (tenant_id, version)
);

alter table messages add column if not exists profile_version integer;

-- Versión 1 de los perfiles que ya existían (para poder volver a ellos).
insert into agent_profile_versions (tenant_id, version, content)
select p.tenant_id, p.version, to_jsonb(p) - 'tenant_id' - 'updated_at' - 'version'
from agent_profiles p
on conflict do nothing;

-- ---------------------------------------------------------------------------
-- 3. Memoria del cliente. `demo_customers` es la tabla de clientes (nombre heredado del MVP).
--    Identidad por canal: en web, una clave del dispositivo; en WhatsApp, el teléfono. Sólo se
--    guarda el hash de la clave.
-- ---------------------------------------------------------------------------
create table if not exists customer_identities (
    tenant_id   uuid not null references tenants(id) on delete cascade,
    channel     text not null check (channel in ('web', 'whatsapp')),
    key_hash    bytea not null,
    customer_id uuid not null references demo_customers(id) on delete cascade,
    created_at  timestamptz not null default now(),
    primary key (tenant_id, channel, key_hash)
);
create index if not exists idx_customer_identities_customer on customer_identities (customer_id);
-- Para el worker: clientes con actividad reciente y conversaciones por cliente.
create index if not exists idx_conversations_customer on conversations (tenant_id, customer_id)
    where customer_id is not null;
create index if not exists idx_conversations_last_message on conversations (last_customer_message_at);

-- 4. Compactación: resumen de la parte vieja de una conversación larga, escrito por el worker en
--    columnas propias (no en agent_state, que reescribe cada turno).
alter table conversations add column if not exists summary text;
alter table conversations add column if not exists summary_until timestamptz;

-- Perfil semántico destilado (hechos cortos), escrito en segundo plano por el worker.
create table if not exists customer_memory (
    customer_id     uuid primary key references demo_customers(id) on delete cascade,
    tenant_id       uuid not null references tenants(id) on delete cascade,
    facts           jsonb not null default '[]'::jsonb,
    processed_until timestamptz,
    updated_at      timestamptz not null default now()
);
create index if not exists idx_customer_memory_tenant on customer_memory (tenant_id);

-- ---------------------------------------------------------------------------
-- 5. Base de conocimiento del negocio: documentos en fragmentos, con búsqueda de texto en español
--    y, si hay modelo de embeddings configurado, vectores (dimensión libre).
-- ---------------------------------------------------------------------------
create table if not exists knowledge_documents (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid not null references tenants(id) on delete cascade,
    title      text not null,
    chars      integer not null default 0,
    created_at timestamptz not null default now(),
    constraint knowledge_documents_tenant_id_id_key unique (tenant_id, id)
);

create table if not exists knowledge_chunks (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references tenants(id) on delete cascade,
    document_id uuid not null,
    position    integer not null,
    content     text not null,
    tsv         tsvector generated always as (to_tsvector('spanish', content)) stored,
    constraint knowledge_chunks_document_fkey foreign key (tenant_id, document_id)
        references knowledge_documents (tenant_id, id) on delete cascade
);
do $$
declare s text;
begin
    select n.nspname into s from pg_extension e join pg_namespace n on n.oid = e.extnamespace
    where e.extname = 'vector';
    if not exists (select 1 from information_schema.columns
                   where table_name = 'knowledge_chunks' and column_name = 'embedding') then
        execute format('alter table knowledge_chunks add column embedding %I.vector', s);
    end if;
    execute format('grant usage on schema %I to app_user', s);
end $$;
create index if not exists idx_knowledge_chunks_tsv on knowledge_chunks using gin (tsv);
create index if not exists idx_knowledge_chunks_tenant on knowledge_chunks (tenant_id, document_id);

-- ---------------------------------------------------------------------------
-- 6. Evaluaciones por negocio: casos que el agente debe pasar antes de activar un perfil.
-- ---------------------------------------------------------------------------
create table if not exists agent_eval_cases (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid not null references tenants(id) on delete cascade,
    message             text not null,
    expect_contains     jsonb not null default '[]'::jsonb,
    expect_not_contains jsonb not null default '[]'::jsonb,
    created_at          timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- RLS: el backend sandbox/público (tenant_isolation) y el panel (app_user, permisiva+restrictiva).
-- La memoria y la identidad del cliente NO se exponen al panel en este corte.
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
    foreach t in array array['agent_profile_versions', 'customer_identities', 'customer_memory',
                             'knowledge_documents', 'knowledge_chunks', 'agent_eval_cases']
    loop
        execute format('alter table %I enable row level security', t);
        execute format('drop policy if exists tenant_isolation on %I', t);
        execute format(
            'create policy tenant_isolation on %I using (tenant_id = nullif(current_setting(''app.current_tenant'', true), '''')::uuid)',
            t);
        execute format('revoke all on %I from anon, authenticated', t);
    end loop;
    foreach t in array array['agent_profile_versions', 'knowledge_documents', 'knowledge_chunks',
                             'agent_eval_cases']
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

grant select, insert         on agent_profile_versions to app_user;
grant select, insert, delete on knowledge_documents    to app_user;
grant select, insert, delete on knowledge_chunks       to app_user;
grant select, insert, delete on agent_eval_cases       to app_user;
