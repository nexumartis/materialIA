-- Presupuesto Vivo — Agente de ventas: stock, carrito/pedidos y pagos
-- Diseño: docs/superpowers/specs/2026-10-26-agente-ventas-design.md (§4, §5).
-- No destructivo e idempotente: create/add if not exists, constraints vía DO, políticas
-- recreadas con drop ... if exists. No toca datos existentes.
--
-- Consistencia de stock: la base es la última barrera. `reserved <= on_hand` y no negativos
-- impiden vender de más aunque el código tenga un bug; el apartado es un UPDATE condicional.

-- ---------------------------------------------------------------------------
-- Catálogo: datos de ficha para el vendedor (marca, descripción, imagen, unidad).
-- ---------------------------------------------------------------------------
alter table catalog_items add column if not exists brand       text;
alter table catalog_items add column if not exists description text not null default '';
alter table catalog_items add column if not exists image_url   text;
alter table catalog_items add column if not exists unit        text not null default 'unidad';

-- Memoria estructurada de la conversación (sólo IDs y la confirmación pendiente; nunca
-- precios ni stock, que se consultan en vivo).
alter table conversations add column if not exists agent_state jsonb not null default '{}'::jsonb;

-- Contenido interactivo del mensaje (tarjetas de producto, botones, link de pago). El texto de
-- `content` sigue siendo la versión completa para canales sin interactividad.
alter table messages add column if not exists payload jsonb;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'catalog_items_tenant_id_id_key') then
        alter table catalog_items add constraint catalog_items_tenant_id_id_key unique (tenant_id, id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'conversations_tenant_id_id_key') then
        alter table conversations add constraint conversations_tenant_id_id_key unique (tenant_id, id);
    end if;
end $$;

-- ---------------------------------------------------------------------------
-- Stock (un depósito por empresa en este corte).
-- ---------------------------------------------------------------------------
create table if not exists stock_levels (
    tenant_id  uuid not null references tenants(id) on delete cascade,
    item_id    uuid not null,
    on_hand    integer not null default 0 check (on_hand >= 0),
    reserved   integer not null default 0 check (reserved >= 0),
    updated_at timestamptz not null default now(),
    primary key (tenant_id, item_id),
    constraint stock_reserved_le_on_hand check (reserved <= on_hand),
    constraint stock_levels_item_fkey foreign key (tenant_id, item_id)
        references catalog_items (tenant_id, id) on delete cascade
);

-- Historial inmutable: cada cambio de stock con su motivo y pedido.
create table if not exists stock_movements (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null references tenants(id) on delete cascade,
    item_id         uuid not null,
    order_id        uuid,
    kind            text not null check (kind in ('restock', 'adjust', 'reserve', 'release', 'sale')),
    delta_on_hand   integer not null default 0,
    delta_reserved  integer not null default 0,
    created_at      timestamptz not null default now()
);
create index if not exists idx_stock_movements_item on stock_movements (tenant_id, item_id, created_at);

-- ---------------------------------------------------------------------------
-- Pedidos. El carrito es un pedido en CART_OPEN (uno por conversación).
-- ---------------------------------------------------------------------------
create table if not exists orders (
    id               uuid primary key default gen_random_uuid(),
    number           bigint generated always as identity,
    tenant_id        uuid not null references tenants(id) on delete cascade,
    conversation_id  uuid references conversations(id) on delete set null,
    customer_id      uuid references demo_customers(id) on delete set null,
    status           text not null default 'CART_OPEN'
                     check (status in ('CART_OPEN', 'PENDING_PAYMENT', 'PAID', 'PREPARING',
                                       'DISPATCHED', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED',
                                       'REFUNDED')),
    currency         text not null default 'ARS',
    subtotal         numeric(14,2) not null default 0 check (subtotal >= 0),
    shipping         numeric(14,2) not null default 0 check (shipping >= 0),
    total            numeric(14,2) not null default 0 check (total >= 0),
    reserved_until   timestamptz,
    cancel_reason    text,
    attention_reason text,
    paid_at          timestamptz,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now(),
    constraint orders_tenant_id_id_key unique (tenant_id, id)
);
-- La conversación del pedido debe ser del MISMO negocio (las FK no pasan por RLS).
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'orders_tenant_conversation_fkey') then
        alter table orders add constraint orders_tenant_conversation_fkey
            foreign key (tenant_id, conversation_id) references conversations (tenant_id, id)
            on delete set null (conversation_id);
    end if;
end $$;
create index if not exists idx_orders_tenant on orders (tenant_id, created_at);
create index if not exists idx_orders_conversation on orders (tenant_id, conversation_id);
create unique index if not exists uq_orders_open_cart
    on orders (tenant_id, conversation_id) where status = 'CART_OPEN';
create index if not exists idx_orders_expiring
    on orders (reserved_until) where status = 'PENDING_PAYMENT';

create table if not exists order_items (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references tenants(id) on delete cascade,
    order_id    uuid not null,
    item_id     uuid not null,
    sku         text not null,
    name        text not null,
    qty         integer not null check (qty > 0),
    unit_price  numeric(14,2) not null check (unit_price >= 0),
    line_total  numeric(14,2) not null check (line_total >= 0),
    constraint order_items_order_item_key unique (order_id, item_id),
    constraint order_items_order_fkey foreign key (tenant_id, order_id)
        references orders (tenant_id, id) on delete cascade,
    constraint order_items_item_fkey foreign key (tenant_id, item_id)
        references catalog_items (tenant_id, id)
);
create index if not exists idx_order_items_order on order_items (tenant_id, order_id);

-- ---------------------------------------------------------------------------
-- Pagos. Una fila por intento de cobro (preferencia); el id de pago del proveedor es único.
-- ---------------------------------------------------------------------------
create table if not exists payments (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid not null references tenants(id) on delete cascade,
    order_id            uuid not null,
    provider            text not null check (provider in ('simulated', 'mercadopago')),
    preference_id       text,
    checkout_url        text,
    provider_payment_id text,
    status              text not null default 'created'
                        check (status in ('created', 'pending', 'in_process', 'approved',
                                          'rejected', 'cancelled', 'refunded', 'charged_back')),
    amount              numeric(14,2) not null check (amount >= 0),
    currency            text not null default 'ARS',
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    constraint payments_order_fkey foreign key (tenant_id, order_id)
        references orders (tenant_id, id) on delete cascade
);
create unique index if not exists uq_payments_provider_payment
    on payments (provider, provider_payment_id) where provider_payment_id is not null;
create unique index if not exists uq_payments_preference
    on payments (provider, preference_id) where preference_id is not null;
create index if not exists idx_payments_order on payments (tenant_id, order_id);

-- Avisos recibidos de los proveedores (auditoría). Sin tenant: se deriva del pedido real
-- consultado al proveedor, nunca del cuerpo del aviso.
create table if not exists payment_notifications (
    id           uuid primary key default gen_random_uuid(),
    provider     text not null,
    request_id   text,
    resource_id  text,
    signature_ok boolean not null,
    outcome      text not null default '',
    received_at  timestamptz not null default now()
);

-- "Servidor" del proveedor simulado: lo que en Mercado Pago vive del lado de ellos.
create table if not exists sim_provider_payments (
    id            uuid primary key default gen_random_uuid(),
    preference_id text not null,
    external_ref  text not null,
    status        text not null,
    amount        numeric(14,2) not null,
    currency      text not null default 'ARS',
    created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- RLS: mismo modelo que 0001 (tenant_isolation para el backend sandbox) y app_user sin acceso
-- hasta que el panel lo necesite. Las tablas sin tenant quedan sin políticas (sólo backend).
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
    foreach t in array array['stock_levels', 'stock_movements', 'orders', 'order_items', 'payments']
    loop
        execute format('alter table %I enable row level security', t);
        execute format('drop policy if exists tenant_isolation on %I', t);
        execute format(
            'create policy tenant_isolation on %I using (tenant_id = nullif(current_setting(''app.current_tenant'', true), '''')::uuid)',
            t);
    end loop;
end $$;
alter table payment_notifications enable row level security;
alter table sim_provider_payments enable row level security;
revoke all on stock_levels, stock_movements, orders, order_items, payments,
              payment_notifications, sim_provider_payments from anon, authenticated;
