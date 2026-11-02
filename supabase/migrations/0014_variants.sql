-- 0014 — Variantes de producto: cada variante sigue siendo un producto (SKU, precio y stock
-- propios) y se agrupa por modelo (`variant_group`) con su etiqueta (`variant_label`, p. ej.
-- «Negro mate»). Columnas `modelo` y `variante` del CSV o la planilla. Idempotente.
alter table catalog_items add column if not exists variant_group text;
alter table catalog_items add column if not exists variant_label text;
create index if not exists idx_catalog_items_variant_group
    on catalog_items (tenant_id, variant_group) where variant_group is not null;
