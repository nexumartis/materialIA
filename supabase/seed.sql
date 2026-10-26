-- Agente de ventas — SEED de datos EXPRESAMENTE FICTICIOS / SINTÉTICOS.
-- Marcas, precios y stock inventados. Dos empresas (C grifería, D ferretería) para verificar
-- el aislamiento multiempresa. Idempotente: on conflict do nothing / where not exists.

-- === Empresa C (grifería y sanitarios) — agente de ventas ========
-- Marcas, precios y stock FICTICIOS. Casos de prueba: última unidad (2 llaves negra),
-- agotado con sustitutos (lavatorio negra) y un producto a pedido (custom_quote).
insert into tenants (id, name, currency) values
  ('0000000c-0000-0000-0000-00000000000c', 'Sanitarios Demo C (SINTÉTICA)', 'ARS')
on conflict (id) do nothing;

insert into catalog_items (id, tenant_id, sku, name, category, pricing_mode, specs_json, currency, brand, description, unit) values
  ('33333333-0000-0000-0000-000000000001','0000000c-0000-0000-0000-00000000000c','GRIF-COC-MONO-NEG-AQ','Canilla de cocina monocomando negra mate','griferia','fixed','{"ambiente":"cocina","tipo":"monocomando","color":"negro","material":"latón","acabado":"negro mate"}'::jsonb,'ARS','Aquaflux (DEMO)','Pico alto giratorio, cartucho cerámico 35 mm.','unidad'),
  ('33333333-0000-0000-0000-000000000002','0000000c-0000-0000-0000-00000000000c','GRIF-COC-MONO-NEG-HL','Canilla de cocina monocomando negra con pico extraíble','griferia','fixed','{"ambiente":"cocina","tipo":"monocomando","color":"negro","material":"latón","acabado":"negro mate"}'::jsonb,'ARS','Hidrolar (DEMO)','Pico extraíble con dos chorros, cartucho cerámico 40 mm.','unidad'),
  ('33333333-0000-0000-0000-000000000003','0000000c-0000-0000-0000-00000000000c','GRIF-COC-2LL-NEG-AQ','Canilla de cocina dos llaves negra','griferia','fixed','{"ambiente":"cocina","tipo":"dos llaves","color":"negro","material":"latón","acabado":"negro mate"}'::jsonb,'ARS','Aquaflux (DEMO)','Montaje a mesada, cierre cerámico.','unidad'),
  ('33333333-0000-0000-0000-000000000004','0000000c-0000-0000-0000-00000000000c','GRIF-COC-MONO-CRO-HL','Canilla de cocina monocomando cromo','griferia','fixed','{"ambiente":"cocina","tipo":"monocomando","color":"cromo","material":"latón","acabado":"cromado"}'::jsonb,'ARS','Hidrolar (DEMO)','Pico tubo giratorio.','unidad'),
  ('33333333-0000-0000-0000-000000000005','0000000c-0000-0000-0000-00000000000c','GRIF-BAN-LAV-NEG-AQ','Canilla de lavatorio monocomando negra','griferia','fixed','{"ambiente":"baño","tipo":"monocomando","color":"negro","material":"latón","acabado":"negro mate"}'::jsonb,'ARS','Aquaflux (DEMO)','Para bacha de apoyo o embutida.','unidad'),
  ('33333333-0000-0000-0000-000000000006','0000000c-0000-0000-0000-00000000000c','GRIF-BAN-LAV-CRO-HL','Canilla de lavatorio monocomando cromo','griferia','fixed','{"ambiente":"baño","tipo":"monocomando","color":"cromo","material":"latón","acabado":"cromado"}'::jsonb,'ARS','Hidrolar (DEMO)','Para bacha de apoyo o embutida.','unidad'),
  ('33333333-0000-0000-0000-000000000007','0000000c-0000-0000-0000-00000000000c','DUCH-TEL-NEG-AQ','Ducha teléfono negra con flexible 1,5 m','duchas','fixed','{"ambiente":"baño","color":"negro","material":"ABS"}'::jsonb,'ARS','Aquaflux (DEMO)','Tres chorros, flexible de acero de 1,5 m.','unidad'),
  ('33333333-0000-0000-0000-000000000008','0000000c-0000-0000-0000-00000000000c','FLEX-AGUA-40','Flexible de conexión de agua 40 cm (par)','repuestos','fixed','{"medida":"40 cm","rosca":"1/2"}'::jsonb,'ARS','Hidrolar (DEMO)','Malla de acero, rosca 1/2".','par'),
  ('33333333-0000-0000-0000-000000000009','0000000c-0000-0000-0000-00000000000c','SIF-PVC-BACHA','Sifón de PVC para bacha','repuestos','fixed','{"material":"PVC"}'::jsonb,'ARS','Hidrolar (DEMO)','Sifón doble con salida de 40 mm.','unidad'),
  ('33333333-0000-0000-0000-000000000010','0000000c-0000-0000-0000-00000000000c','INOD-LARGO-BLA','Inodoro largo blanco (a pedido)','sanitarios','custom_quote','{"color":"blanco","ambiente":"baño"}'::jsonb,'ARS','Aquaflux (DEMO)','Se encarga a fábrica: requiere confirmar plazo con una persona.','unidad')
on conflict (id) do nothing;

insert into price_entries (tenant_id, item_id, amount, currency, valid_from, valid_until)
select '0000000c-0000-0000-0000-00000000000c'::uuid, v.item_id, v.amount, 'ARS', date '2026-01-01', null::date
from (values
  ('33333333-0000-0000-0000-000000000001'::uuid,  89900.00),
  ('33333333-0000-0000-0000-000000000002'::uuid, 129000.00),
  ('33333333-0000-0000-0000-000000000003'::uuid,  74500.00),
  ('33333333-0000-0000-0000-000000000004'::uuid,  68000.00),
  ('33333333-0000-0000-0000-000000000005'::uuid,  59900.00),
  ('33333333-0000-0000-0000-000000000006'::uuid,  52000.00),
  ('33333333-0000-0000-0000-000000000007'::uuid,  34500.00),
  ('33333333-0000-0000-0000-000000000008'::uuid,   6800.00),
  ('33333333-0000-0000-0000-000000000009'::uuid,   9200.00)
) as v(item_id, amount)
where not exists (
  select 1 from price_entries p
  where p.tenant_id = '0000000c-0000-0000-0000-00000000000c' and p.item_id = v.item_id
    and p.valid_from = date '2026-01-01'
);

insert into stock_levels (tenant_id, item_id, on_hand) values
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000001', 6),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000002', 3),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000003', 1),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000004', 10),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000005', 0),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000006', 8),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000007', 5),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000008', 40),
  ('0000000c-0000-0000-0000-00000000000c','33333333-0000-0000-0000-000000000009', 15)
on conflict (tenant_id, item_id) do nothing;

insert into demo_customers (id, tenant_id, display_name, contact_data, consent_status) values
  ('cccc0000-0000-0000-0000-00000000000c','0000000c-0000-0000-0000-00000000000c','Cliente Demo C','{"canal":"web_sandbox"}'::jsonb,'unknown')
on conflict (id) do nothing;


-- === Empresa D (ferretería) — segunda empresa para aislamiento ====
-- Casos de catálogo: precio vigente, precio VENCIDO (no se afirma) y producto a medida.
insert into tenants (id, name, currency) values
  ('0000000d-0000-0000-0000-00000000000d', 'Ferretería Demo D (SINTÉTICA)', 'ARS')
on conflict (id) do nothing;

insert into catalog_items (id, tenant_id, sku, name, category, pricing_mode, specs_json, currency, brand) values
  ('44444444-0000-0000-0000-000000000001','0000000d-0000-0000-0000-00000000000d','FER-MART-500','Martillo carpintero 500 g','herramientas','fixed','{"peso":"500 g"}'::jsonb,'ARS','Forjax (DEMO)'),
  ('44444444-0000-0000-0000-000000000002','0000000d-0000-0000-0000-00000000000d','FER-TALAD-650','Taladro percutor 650 W (precio vencido)','herramientas','fixed','{"potencia":"650 W"}'::jsonb,'ARS','Forjax (DEMO)'),
  ('44444444-0000-0000-0000-000000000003','0000000d-0000-0000-0000-00000000000d','FER-REJA-MED','Reja de hierro a medida','herreria','custom_quote','{"material":"hierro"}'::jsonb,'ARS','Taller Demo')
on conflict (id) do nothing;

insert into price_entries (tenant_id, item_id, amount, currency, valid_from, valid_until)
select '0000000d-0000-0000-0000-00000000000d'::uuid, v.item_id, v.amount, 'ARS', v.valid_from, v.valid_until
from (values
  ('44444444-0000-0000-0000-000000000001'::uuid, 18500.00, date '2026-01-01', null::date),
  ('44444444-0000-0000-0000-000000000002'::uuid, 96000.00, date '2025-01-01', date '2025-12-31')
) as v(item_id, amount, valid_from, valid_until)
where not exists (
  select 1 from price_entries p
  where p.tenant_id = '0000000d-0000-0000-0000-00000000000d' and p.item_id = v.item_id
    and p.valid_from = v.valid_from
);

insert into stock_levels (tenant_id, item_id, on_hand) values
  ('0000000d-0000-0000-0000-00000000000d','44444444-0000-0000-0000-000000000001', 12)
on conflict (tenant_id, item_id) do nothing;

-- Fotos de demo (ilustraciones propias servidas por el backend en /static/products).
update catalog_items set image_url = '/static/products/' || lower(sku) || '.svg'
where tenant_id = '0000000c-0000-0000-0000-00000000000c' and image_url is null;
