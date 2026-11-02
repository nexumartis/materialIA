-- 0019 — Venta cruzada: SKUs que el negocio sugiere junto a cada producto (columna `complementos`
-- del CSV / planilla). El agente sólo ofrece estos, con stock y precio vigentes. Idempotente.
alter table catalog_items add column if not exists complements text[] not null default '{}';
