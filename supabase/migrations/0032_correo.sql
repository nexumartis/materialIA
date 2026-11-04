-- Envíos por correo (Andreani, OCA, Correo Argentino…): el negocio despacha, carga el correo y el número
-- de seguimiento, y el cliente lo recibe en su charla. Sin integración con el correo: el número lo carga
-- una persona (la cotización y la etiqueta automáticas quedan para cuando un negocio aporte su contrato).

alter table orders add column if not exists carrier text check (char_length(carrier) <= 40);
alter table orders add column if not exists tracking_code text check (char_length(tracking_code) <= 60);
alter table orders add column if not exists shipped_at timestamptz;
