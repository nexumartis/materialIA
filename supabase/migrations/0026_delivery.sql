-- 0026 — Entrega del pedido: envío a domicilio (dirección normalizada con Georef, zona y costo
-- cargados por el negocio) o retiro en el local, con contacto para coordinar. Idempotente.
alter table orders add column if not exists delivery_method text;
alter table orders drop constraint if exists orders_delivery_method_check;
alter table orders add constraint orders_delivery_method_check check (delivery_method is null or delivery_method in ('pickup', 'delivery'));
alter table orders add column if not exists delivery_address jsonb;
alter table orders add column if not exists delivery_contact jsonb;
alter table orders add column if not exists delivery_note text check (delivery_note is null or char_length(delivery_note) <= 300);
