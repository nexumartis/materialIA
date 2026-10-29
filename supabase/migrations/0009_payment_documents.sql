-- 0009 — Comprobantes de pago que adjunta el comprador a su pedido.
--
-- Sólo información para que el dueño revise: un archivo o su OCR NUNCA acreditan un pago (eso lo
-- hacen el proveedor o el dueño con confirm_transfer, 0008). Original en bytea privado: atajo
-- para la demo con datos sintéticos (≤10 MiB); pasar a almacenamiento privado antes de un piloto.
-- Idempotente; sin DROP de datos.

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

-- RLS: mismo modelo que receipts (0008). El panel lee y sólo decide (columnas de decisión).
alter table payment_documents enable row level security;
drop policy if exists tenant_isolation on payment_documents;
create policy tenant_isolation on payment_documents
    using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid);
drop policy if exists member_access on payment_documents;
create policy member_access on payment_documents for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
drop policy if exists member_only on payment_documents;
create policy member_only on payment_documents as restrictive for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
revoke all on payment_documents from anon, authenticated;
grant select on payment_documents to app_user;
grant update (decision, decided_by, decided_at) on payment_documents to app_user;
