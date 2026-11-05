-- El uso de IA de las fotos del cliente («foto») cuenta en el tope diario del negocio como el resto.
alter table llm_usage drop constraint if exists llm_usage_kind_check;
alter table llm_usage add constraint llm_usage_kind_check check (kind in ('venta', 'resumen', 'memoria', 'otro', 'foto'));
