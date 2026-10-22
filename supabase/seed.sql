-- Presupuesto Vivo — SEED de datos EXPRESAMENTE FICTICIOS / SINTÉTICOS.
-- No usar precios/medidas de ninguna demo previa como si fueran reales.
-- Dos empresas A/B para verificar aislamiento multiempresa.
-- Idempotente: on conflict do nothing (se puede correr varias veces).

-- === Empresas ====================================================
insert into tenants (id, name, currency) values
  ('0000000a-0000-0000-0000-00000000000a', 'Cristalería Demo A (SINTÉTICA)', 'ARS'),
  ('0000000b-0000-0000-0000-00000000000b', 'Aberturas Demo B (SINTÉTICA)', 'ARS')
on conflict (id) do nothing;

-- === Catálogo Empresa A (mamparas de vidrio a medida) ============
-- La mayoría son "custom_quote" (a medida -> requiere cotización/visita humana).
insert into catalog_items (id, tenant_id, sku, name, category, pricing_mode, specs_json, currency) values
  ('11111111-0000-0000-0000-000000000001','0000000a-0000-0000-0000-00000000000a','MAMP-COR-NEG-160','Mampara corrediza negra 1,60 (DEMO, a medida)','mampara','custom_quote','{"tipo":"corrediza","color":"negro","material":"aluminio","ancho_mm":1600}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000002','0000000a-0000-0000-0000-00000000000a','MAMP-COR-NEG-180','Mampara corrediza negra 1,80 (DEMO, a medida)','mampara','custom_quote','{"tipo":"corrediza","color":"negro","material":"aluminio","ancho_mm":1800}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000003','0000000a-0000-0000-0000-00000000000a','MAMP-COR-NEG-200','Mampara corrediza negra 2,00 (DEMO, a medida)','mampara','custom_quote','{"tipo":"corrediza","color":"negro","material":"aluminio","ancho_mm":2000}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000004','0000000a-0000-0000-0000-00000000000a','MAMP-COR-BLA-140','Mampara corrediza blanca 1,40 (DEMO, a medida)','mampara','custom_quote','{"tipo":"corrediza","color":"blanco","material":"aluminio","ancho_mm":1400}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000005','0000000a-0000-0000-0000-00000000000a','MAMP-FIJ-PLA-080','Paño fijo plata 0,80 (DEMO, a medida)','mampara','custom_quote','{"tipo":"fija","color":"plata","material":"aluminio","ancho_mm":800}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000006','0000000a-0000-0000-0000-00000000000a','VIDR-TEMP-6MM-M2','Vidrio templado 6mm por m² (DEMO, requiere visita)','vidrio','custom_quote','{"espesor_mm":6,"requiere_visita":true}'::jsonb,'ARS'),
  -- Accesorios con precio de lista (pricing_mode = fixed)
  ('11111111-0000-0000-0000-000000000007','0000000a-0000-0000-0000-00000000000a','KIT-INST-STD','Kit de instalación estándar (DEMO)','accesorio','fixed','{"incluye":"tornillería y sellado básico"}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000008','0000000a-0000-0000-0000-00000000000a','PERF-ALU-NEG-ML','Perfil de aluminio negro x metro (DEMO)','accesorio','fixed','{"color":"negro","unidad":"metro"}'::jsonb,'ARS'),
  ('11111111-0000-0000-0000-000000000009','0000000a-0000-0000-0000-00000000000a','SELL-SILIC-X1','Sellador siliconado x1 (DEMO, precio vencido)','accesorio','fixed','{"unidad":"pomo"}'::jsonb,'ARS')
on conflict (id) do nothing;

-- Precios Empresa A: dos vigentes y uno VENCIDO (para probar "precio no afirmable").
insert into price_entries (tenant_id, item_id, amount, currency, valid_from, valid_until) values
  ('0000000a-0000-0000-0000-00000000000a','11111111-0000-0000-0000-000000000007', 85000.00, 'ARS', date '2026-01-01', null),
  ('0000000a-0000-0000-0000-00000000000a','11111111-0000-0000-0000-000000000008', 12000.00, 'ARS', date '2026-01-01', null),
  ('0000000a-0000-0000-0000-00000000000a','11111111-0000-0000-0000-000000000009',  9000.00, 'ARS', date '2025-01-01', date '2025-12-31')
on conflict do nothing;

-- === Catálogo Empresa B (aberturas) — distinto a A ===============
insert into catalog_items (id, tenant_id, sku, name, category, pricing_mode, specs_json, currency) values
  ('22222222-0000-0000-0000-000000000001','0000000b-0000-0000-0000-00000000000b','VENT-ALU-BLA-120','Ventana corrediza blanca 1,20 (DEMO, a medida)','ventana','custom_quote','{"tipo":"corrediza","color":"blanco","material":"aluminio","ancho_mm":1200}'::jsonb,'ARS'),
  ('22222222-0000-0000-0000-000000000002','0000000b-0000-0000-0000-00000000000b','PUER-ALU-NEG-090','Puerta de aluminio negra 0,90 (DEMO, a medida)','puerta','custom_quote','{"tipo":"abrir","color":"negro","material":"aluminio","ancho_mm":900}'::jsonb,'ARS'),
  ('22222222-0000-0000-0000-000000000003','0000000b-0000-0000-0000-00000000000b','MOSQ-STD','Mosquitero estándar (DEMO)','accesorio','fixed','{"tipo":"corredizo"}'::jsonb,'ARS')
on conflict (id) do nothing;

insert into price_entries (tenant_id, item_id, amount, currency, valid_from, valid_until) values
  ('0000000b-0000-0000-0000-00000000000b','22222222-0000-0000-0000-000000000003', 45000.00, 'ARS', date '2026-01-01', null)
on conflict do nothing;

-- === Clientes ficticios =========================================
insert into demo_customers (id, tenant_id, display_name, contact_data, consent_status) values
  ('aaaa0000-0000-0000-0000-00000000000a','0000000a-0000-0000-0000-00000000000a','Cliente Demo A','{"canal":"web_sandbox"}'::jsonb,'unknown'),
  ('bbbb0000-0000-0000-0000-00000000000b','0000000b-0000-0000-0000-00000000000b','Cliente Demo B','{"canal":"web_sandbox"}'::jsonb,'unknown')
on conflict (id) do nothing;
