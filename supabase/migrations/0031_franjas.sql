-- Franjas de entrega elegidas por el cliente en el chat: el agente ofrece día y franja con cupo
-- (priorizando donde ya hay entregas cerca) y, cuando el pedido queda pagado, la entrega se agenda
-- sola. La configuración (días, franjas, cupo) vive en tenants.settings_json → «delivery_slots».

alter table orders add column if not exists delivery_date date;
alter table orders add column if not exists delivery_window text;
do $$ begin
    alter table orders add constraint orders_delivery_window_check check (delivery_window in ('am', 'pm', 'day'));
exception when duplicate_object then null; end $$;
-- Cupo ocupado por pedidos que todavía esperan el pago (con reserva vigente).
create index if not exists orders_delivery_slot_idx on orders (tenant_id, delivery_date, delivery_window)
    where delivery_date is not null;

alter table delivery_jobs add column if not exists source text not null default 'panel';
do $$ begin
    alter table delivery_jobs add constraint delivery_jobs_source_check check (source in ('panel', 'chat'));
exception when duplicate_object then null; end $$;
