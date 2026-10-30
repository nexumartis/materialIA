-- 0012 — Ficha técnica del producto (PDF del fabricante): el agente la ofrece en vez de describir
-- medidas que no puede inventar. Link https cargado por el dueño (columna `ficha_url` del CSV o
-- la planilla). Idempotente.
alter table catalog_items add column if not exists datasheet_url text;
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'catalog_items_datasheet_https') then
        alter table catalog_items add constraint catalog_items_datasheet_https
            check (datasheet_url is null or datasheet_url ~ '^https://');
    end if;
end $$;
