-- 0020 — Encuesta de satisfacción: el comprador califica (1 a 5, comentario opcional) un pedido
-- PAGADO de su conversación. Una calificación por pedido (se puede corregir). El panel la ve por
-- negocio con RLS. Idempotente.
create table if not exists order_ratings (
    tenant_id       uuid not null references tenants(id) on delete cascade,
    order_id        uuid not null,
    conversation_id uuid references conversations(id) on delete set null,
    score           smallint not null check (score between 1 and 5),
    comment         text check (comment is null or char_length(comment) <= 500),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    primary key (tenant_id, order_id),
    constraint order_ratings_order_fkey foreign key (tenant_id, order_id)
        references orders (tenant_id, id) on delete cascade
);
create index if not exists idx_order_ratings_created on order_ratings (tenant_id, created_at);
alter table order_ratings enable row level security;
grant select on order_ratings to app_user;
drop policy if exists member_access on order_ratings;
drop policy if exists member_only   on order_ratings;
create policy member_access on order_ratings for select to app_user using (tenant_id = app_member_tenant());
create policy member_only   on order_ratings as restrictive for all to app_user using (tenant_id = app_member_tenant());
