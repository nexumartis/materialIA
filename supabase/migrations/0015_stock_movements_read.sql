-- 0015 — El panel puede LEER el historial de movimientos de stock de su negocio (ventas, reservas,
-- liberaciones y ajustes). Las políticas member_access/member_only ya existen (0005). Idempotente.
grant select on stock_movements to app_user;
