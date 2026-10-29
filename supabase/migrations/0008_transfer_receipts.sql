-- 0008 — Comprobantes de clientes, transferencia verificada por el dueño y constancia de compra.
--
-- Una transferencia la acredita el DUEÑO cotejando su banco (nunca un archivo/OCR): queda como
-- pago `transfer` con actor y fecha. Su id es '<tenant>:<referencia>', así una referencia
-- bancaria no paga dos pedidos del mismo negocio (uq_payments_provider_payment).
-- La constancia se emite una sola vez por pedido, en la misma transacción que lo deja PAID.
-- Idempotente; sin DROP de datos.

alter table payments drop constraint if exists payments_provider_check;
alter table payments add constraint payments_provider_check
    check (provider in ('simulated', 'mercadopago', 'transfer'));
alter table payments add column if not exists verified_at timestamptz;
alter table payments add column if not exists verified_by uuid references auth.users(id) on delete set null;
alter table payments add column if not exists reversed_at timestamptz;

-- Instantánea estable de la compra (negocio, pedido, productos, importe, pago verificado).
-- El PDF se arma a demanda desde `snapshot`; no es factura fiscal.
create table if not exists receipts (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references tenants(id) on delete cascade,
    order_id    uuid not null,
    payment_id  uuid not null references payments(id),
    snapshot    jsonb not null,
    issued_at   timestamptz not null default now(),
    constraint receipts_order_key unique (tenant_id, order_id),
    constraint receipts_order_fkey foreign key (tenant_id, order_id)
        references orders (tenant_id, id) on delete cascade
);

-- Comprobantes que adjunta el comprador a su pedido. Sólo información para que el dueño revise:
-- un archivo o su OCR NUNCA acreditan un pago. Original en bytea privado: atajo para la demo
-- con datos sintéticos (≤10 MiB); pasar a almacenamiento privado antes de un piloto real.
create table if not exists payment_documents (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    order_id        uuid not null,
    conversation_id uuid not null,
    sha256          text not null,
    mime            text not null check (mime in ('image/jpeg', 'image/png', 'application/pdf')),
    size            integer not null check (size > 0),
    content         bytea not null,
    status          text not null default 'received'
                    check (status in ('received', 'processing', 'read', 'unreadable')),
    attempts        integer not null default 0,
    claimed_at      timestamptz,
    pages           integer,
    ocr             jsonb,          -- campos sugeridos y líneas (ocr.read_document); nunca a messages
    error           text,
    decision        text check (decision in ('linked', 'rejected')),
    decided_by      uuid references auth.users(id) on delete set null,
    decided_at      timestamptz,
    payment_id      uuid references payments(id),
    received_at     timestamptz not null default now(),
    constraint payment_documents_file_key unique (tenant_id, sha256),
    constraint payment_documents_order_fkey foreign key (tenant_id, order_id)
        references orders (tenant_id, id) on delete cascade,
    constraint payment_documents_conversation_fkey foreign key (tenant_id, conversation_id)
        references conversations (tenant_id, id) on delete cascade
);
create index if not exists idx_payment_documents_order on payment_documents (tenant_id, order_id);
create index if not exists idx_payment_documents_pending
    on payment_documents (received_at) where status in ('received', 'processing');

-- RLS: mismo modelo que 0004/0005 (tenant_isolation del backend + member_access/member_only
-- del panel). El panel lee constancias y comprobantes y sólo decide sobre estos últimos.
do $$
declare t text;
begin
    foreach t in array array['receipts', 'payment_documents']
    loop
        execute format('alter table %I enable row level security', t);
        execute format('drop policy if exists tenant_isolation on %I', t);
        execute format(
            'create policy tenant_isolation on %I using (tenant_id = nullif(current_setting(''app.current_tenant'', true), '''')::uuid)',
            t);
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
revoke all on receipts, payment_documents from anon, authenticated;
grant select on receipts, payment_documents to app_user;
grant update (decision, decided_by, decided_at) on payment_documents to app_user;
