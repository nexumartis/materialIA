-- 0008 — Transferencia verificada por el dueño y constancia comercial de compra.
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

-- RLS: mismo modelo que 0004/0005 (tenant_isolation del backend + member_access/member_only
-- del panel). El panel sólo lee constancias; las emite el backend.
alter table receipts enable row level security;
drop policy if exists tenant_isolation on receipts;
create policy tenant_isolation on receipts
    using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid);
drop policy if exists member_access on receipts;
create policy member_access on receipts for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
drop policy if exists member_only on receipts;
create policy member_only on receipts as restrictive for all to app_user
    using (tenant_id = app_member_tenant()) with check (tenant_id = app_member_tenant());
revoke all on receipts from anon, authenticated;
grant select on receipts to app_user;
