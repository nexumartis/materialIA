-- Chat público: prueba de pertenencia del comprador por conversación.
-- Al crear una conversación desde la tienda pública el servidor emite un token aleatorio y guarda
-- sólo su SHA-256 acá; cada lectura y escritura pública lo exige. Null = conversación del
-- sandbox/demo (no se abre desde la tienda pública, y el sandbox no abre las que tienen token).
-- No destructivo e idempotente.

alter table conversations add column if not exists access_token_hash bytea;
