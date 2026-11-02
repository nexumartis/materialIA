-- 0017 — Seña para productos a pedido. El dueño arma un pedido a medida (precio que confirma una
-- persona) con una seña opcional: se cobra primero la seña y después el saldo, cada uno con pago
-- verificado (proveedor o transferencia cotejada). Spec: docs/superpowers/specs/2026-11-02-sena-design.md.
-- Idempotente y no destructivo: el check de estados se reemplaza por uno más amplio.
alter table orders add column if not exists quote boolean not null default false;
alter table orders add column if not exists deposit numeric(14,2);
alter table orders add column if not exists deposit_paid_at timestamptz;

alter table orders drop constraint if exists orders_deposit_check;
alter table orders add constraint orders_deposit_check check (deposit is null or (deposit > 0 and deposit < total));

alter table orders drop constraint if exists orders_status_check;
alter table orders add constraint orders_status_check
    check (status in ('CART_OPEN', 'PENDING_PAYMENT', 'DEPOSIT_PAID', 'PAID', 'PREPARING', 'DISPATCHED',
                      'IN_TRANSIT', 'DELIVERED', 'CANCELLED', 'REFUNDED'));

-- Qué cobra cada link/pago: null = el pedido entero; 'deposit' = la seña; 'balance' = el saldo.
-- Un link por cobro (la reutilización se busca por este campo, no por el monto que informa el aviso).
alter table payments add column if not exists charge text;
alter table payments drop constraint if exists payments_charge_check;
alter table payments add constraint payments_charge_check check (charge is null or charge in ('deposit', 'balance'));
