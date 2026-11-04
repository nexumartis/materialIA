# Auditoría de escalabilidad — 04/11/2026

Pregunta: ¿qué se rompe cuando lo usan 100, 1.000 y 10.000 negocios? Fue una auditoría de **sólo lectura**: no se cambió código, no se commiteó y no se tocó la nube. Las mediciones se hicieron en la DB descartable `127.0.0.1:55436` con datos sintéticos acotados, dentro de transacciones que terminaron en `ROLLBACK`. Después se verificó que no quedaran filas sintéticas (0 tenants `synthetic-%` y 0 usuarios `synthetic@example.invalid`). Antes se frenó el worker con `pkill -f app.worker`. Se aplicaron las skills `performance-optimization` y `security-and-hardening`.

## Resumen (5 líneas)

1. **El tope global de IA (40 M tokens y 20.000 llamadas por día) se agota con unos 100 negocios chicos** y es «el primero que llega se lo lleva»: unos pocos negocios, o cuentas falsas, apagan la IA de todos.
2. **Las políticas RLS hacen el panel ~330× más lento** cuando un negocio tiene mucha historia: contar 200k mensajes tarda 10,9 ms sin RLS y 3.618 ms con `app_user` (`app_member_tenant()` se evalúa fila por fila).
3. **El worker es un único bucle en serie, sin tiempo máximo para las tareas de IA** y sin aislar errores: una IA lenta o un error demora la liberación de stock y frena las demás tareas. Además, sus consultas globales crecen con toda la base.
4. **El aislamiento entre negocios de las rutas públicas y del worker depende sólo del código**: el backend corre como `postgres`, que ignora RLS, así que `app.current_tenant` no protege nada hoy.
5. **Hay un solo Mercado Pago para toda la plataforma, no hay retención de datos y la observabilidad es casi nula** (ni métricas, ni trazas, ni id de request, ni `statement_timeout`). Con 1.000 negocios eso ya es inoperable.

## Mediciones (DB descartable, Postgres local, en caliente)

| Consulta | Datos sintéticos | Tiempo | Plan |
|---|---|---|---|
| `limits.ai_allowed` (suma global del día) | 720k filas en `llm_usage` (2.000 negocios × 4 tipos × 90 días) | **64 ms** por llamada | Parallel Seq Scan: la PK empieza por `tenant_id` y el filtro es por `day` |
| Bandeja `inbox.list_conversations` (negocio grande) | 20k conversaciones, 200k mensajes | 62 ms | 20.000 lateral joins y después ordena: no corta por el `limit` |
| `compaction.compact_due` (global, en cada vuelta) | 30,7k conversaciones activas, 342k mensajes | **265 ms** y 0 filas | Recorre todos los mensajes de 7 días y agrupa |
| `customer_memory.refresh_due` | (pocos clientes) | 0,1 ms | Bien con este volumen |
| `evals.cleanup_stale` | 30k conversaciones | 2,4 ms | Seq Scan (no hay índice por `channel`) |
| `count(*)` de mensajes de un negocio, rol `postgres` | 200k mensajes | **10,9 ms** | — |
| Lo mismo con rol `app_user` (RLS, como en el panel) | 200k mensajes | **3.618 ms** | `Filter: (tenant_id = current_setting(...)) OR (tenant_id = app_member_tenant())`, una vez por fila |

Las cifras de 1.000 y 10.000 negocios son **extrapolaciones lineales** de estas mediciones, no pruebas de carga.

---

## Hallazgos por severidad

### CRÍTICOS

**C1. El tope global de IA es fijo, chico y no reparte entre negocios.**
- **Dónde:** `backend/app/config.py:56-59` (`ai_daily_tokens_per_tenant=3_000_000`, `ai_daily_calls_global=20_000`, `ai_daily_tokens_global=40_000_000`) y `backend/app/domain/limits.py:128-164`.
- **Evidencia:** con los supuestos de costo (abajo), una conversación consume unos 80k tokens. El tope global alcanza para **unas 500 conversaciones por día en total**, y el tope por negocio para unas 37. Con 13 negocios en su tope se agota el global (13 × 3 M = 39 M de 40 M). Pasado el tope, `ai_allowed` devuelve `False` para **todos** los negocios hasta el día siguiente.
- **Impacto:**
  - **100 negocios** (300 conv/mes cada uno ≈ 1.000 conv/día): el global se agota cerca del mediodía y la tarde se atiende sin IA.
  - **1.000 negocios:** la IA dura los primeros minutos del día.
  - **10.000 negocios:** no hay IA.
  - Además, un negocio con mucho tráfico o un atacante con 13 cuentas gratis apaga la IA de todos (vecino ruidoso).
- **Arreglo:** el tope global tiene que ser un freno de emergencia, no un cupo para repartir; que escale con la cantidad de negocios activos, o que se reemplace por el tope mensual del proveedor más una alerta. Lo que limita de verdad debería ser un cupo **por negocio según su plan**, y con IA reservada por negocio, de modo que uno no pueda comerse lo de otro. Los negocios nuevos y sin verificar, con cupo chico. **Esfuerzo: M.**

**C2. RLS evalúa `app_member_tenant()` en cada fila: el panel se vuelve lento con negocios grandes.**
- **Dónde:** las políticas de `supabase/migrations/0003_accounts.sql:81-106` (y las que copian el patrón en migraciones posteriores), junto con las políticas permisivas `tenant_isolation` (`0001_init.sql:154`, `0004_commerce.sql:184`, `0007_agent_architecture.sql:131`, entre otras), que se combinan con `OR`. Las usan las 53 rutas del panel con `user_tx` (`backend/app/db.py:80-100`).
- **Evidencia:** la misma consulta tarda 10,9 ms con `postgres` y 3.618 ms con `app_user`, unos 18 µs por fila. La función es `security definer`, así que no se inlinea, y el `OR` impide evaluarla una sola vez.
- **Impacto:**
  - **100 negocios:** se nota poco.
  - **1.000 negocios:** los negocios con más de 100k mensajes ven tableros (`insights.summary`, que recorre mensajes, pedidos y conversaciones del período) de varios segundos.
  - **10.000 negocios:** timeouts del panel y conexiones del pool ocupadas por segundos, lo que degrada también el chat público, porque es el mismo pool.
- **Arreglo:** escribir las políticas como `tenant_id = (select app_member_tenant())`, que se evalúa una vez como InitPlan (es el patrón que recomienda Supabase). Además, quitar o hacer `restrictive` el `tenant_isolation` para `app_user`, así no queda un `OR`. Medir antes y después con la misma consulta. Va en una migración idempotente. **Esfuerzo: S.**

**C3. El worker es un solo bucle en serie, sin tiempo máximo para la IA y sin aislar errores.**
- **Dónde:** `backend/app/worker.py:26-35`, `customer_memory.refresh_due` (`domain/customer_memory.py:202-217`), `compaction.compact_due` (`agent/compaction.py:78-92`) y `handoff.summarize_due` (`domain/handoff.py:112`).
- **Evidencia:**
  - Memoria y compactación procesan hasta 20 elementos cada una, y resúmenes de derivación hasta 10, con hasta 60 s por llamada (`llm_timeout_s`). Una vuelta puede tardar **50 minutos** si el modelo está lento. `expire_reservations` corre primero, pero en la vuelta *siguiente*, así que el stock de pedidos vencidos queda apartado todo ese tiempo.
  - `refresh_due` y `compact_due` no tienen `try` por elemento: una excepción corta todo `run_once` (es un diccionario que se evalúa en orden), y ese minuto no corren OCR, planillas, webhooks ni resúmenes.
- **Impacto:**
  - **100 negocios:** demoras ocasionales.
  - **1.000 negocios:** la cola de memoria y resúmenes crece más rápido de lo que se procesa (~7/min necesarios contra 20 por vuelta lenta) y las reservas se liberan tarde.
  - **10.000 negocios:** un solo worker no alcanza para nada.
- **Arreglo:**
  1. Darles a las tareas de IA un `budget_s`, como ya tienen OCR, planillas y webhooks.
  2. Poner `try/except` por tarea en `run_once` y por elemento en `refresh_due` y `compact_due`.
  3. Correr `expire_reservations` en su propio bucle corto o como `pg_cron`.
  4. Separar las tareas de IA en otro proceso o cola.

  **Esfuerzo:** S para los pasos 1 y 2, M para los pasos 3 y 4.

**C4. Las tareas de IA del worker esperan al modelo con una conexión y una transacción abiertas.**
- **Dónde:** `customer_memory.refresh` (`domain/customer_memory.py:158-196`) y `compaction.compact` (`agent/compaction.py:39-75`): `tenant_tx` sigue abierta durante `llm_tasks.ask_json`.
- **Evidencia:** el pool es de `max_size=10` por proceso (`backend/app/db.py:27-31`). Cada llamada al modelo puede tardar hasta 60 s con la conexión en «idle in transaction». Lo correcto ya está hecho en `handoff.summarize`, que lee, cierra y después llama al modelo.
- **Impacto:** desde **1.000 negocios**, con varios workers, se agotan las conexiones de Supabase (el pooler de sesión tiene un límite bajo) y las transacciones largas frenan el autovacuum en tablas calientes.
- **Arreglo:** el mismo patrón de `handoff.summarize`: leer, cerrar la transacción, llamar al modelo y escribir en otra transacción. El lock consultivo de esa transacción se reemplaza por un reclamo (`claimed_at` o `processed_until` provisorio). **Esfuerzo: S–M.**

**C5. Un único Mercado Pago para toda la plataforma.**
- **Dónde:** `backend/app/payments/providers.py:136-139`: un solo `MP_ACCESS_TOKEN` global.
- **Evidencia:** todas las preferencias de todos los negocios se crean con la misma cuenta, así que la plata entra a la plataforma y no al negocio. Además comparten un mismo cupo de API.
- **Impacto:** no aplica a la fase actual (sin producción), pero **bloquea los pilotos reales desde el primer negocio** y, a escala, el cupo compartido y el riesgo legal y contable.
- **Arreglo:** credenciales por negocio (OAuth de Mercado Pago o modelo marketplace), cifradas y guardadas por negocio, y un cliente por negocio. Es una decisión de producto y legal. **Esfuerzo: L.**

### ALTOS

**A1. `ai_allowed` suma toda la tabla `llm_usage` del día sin índice.**
- **Dónde:** `backend/app/domain/limits.py:142-149`. La PK de `llm_usage` es `(tenant_id, day, kind, model)` (`0013_llm_usage.sql:11`).
- **Evidencia:** 64 ms (Seq Scan) con 720k filas. La tabla crece sin borrarse: con 10k negocios × 4 tipos × 365 días son unos 15 M de filas por año, más de 1 s por llamada. Se cachea 5 s **por negocio y por proceso**, y se llama en cada turno y en cada paso del planner.
- **Impacto:** **100:** despreciable. **1.000:** decenas de ms por turno. **10.000:** segundos por turno y CPU de la DB ocupada.
- **Arreglo:** un índice `llm_usage (day)` y/o una tabla resumen `llm_usage_daily_total(day)` con upsert. Retención: agregar por mes lo que tenga más de 90 días. **Esfuerzo: S.**

**A2. Consultas globales del worker en cada vuelta, que crecen con toda la base.**
- **Dónde:** `compact_due` (265 ms con 342k mensajes, `agent/compaction.py:80-88`), `refresh_due`, `cleanup_stale` (Seq Scan, `domain/evals.py:105`) y `deliver_due`.
- **Impacto:**
  - **1.000 negocios:** unos 3 M de mensajes por semana, ~2–3 s por vuelta sólo en `compact_due`.
  - **10.000 negocios:** decenas de segundos de CPU de la DB por minuto y por worker.
- **Arreglo:**
  - Un contador `conversations.message_count` (o `unsummarized_count`) que se mantenga al insertar, más un índice parcial de pendientes de resumir.
  - Para `cleanup_stale`, un índice parcial `(created_at) where channel = 'eval'`.

  **Esfuerzo: M.**

**A3. Sin reparto justo entre negocios en el worker.**
- **Dónde:**
  - webhooks (`domain/webhooks.py:165-200`): una cola global FIFO por `next_attempt_at`, con 5 s de timeout por envío y 30 s de presupuesto por vuelta;
  - planillas (`domain/catalog_sheet.py:194-214`): 10 por vuelta;
  - memoria y compactación: `limit 20` sin orden.
- **Evidencia:** un negocio que genera 1.000 eventos hacia un endpoint que tarda 4,9 s deja la entrega en unos **6 envíos por minuto para toda la plataforma**. Con las planillas, hacen falta N/15 sincronizaciones por minuto: 100 negocios necesitan 7/min (alcanza justo), 1.000 necesitan 67/min contra un máximo de 10, y 10.000 necesitan 667/min.
- **Impacto:** **1.000:** las planillas se sincronizan cada ~100 min en lugar de 15, y los webhooks se atrasan horas. **10.000:** colapso.
- **Arreglo:**
  - Elegir por negocio en ronda (`distinct on (tenant_id)` o una ventana por negocio) y poner un tope de envíos en curso por endpoint.
  - Un circuit breaker por endpoint que falla: pausarlo y avisar.
  - Hacer las descargas en paralelo, con un pool de hilos o asyncio.

  **Esfuerzo: M.**

**A4. Varios workers duplican trabajo y gasto de IA.**
- **Dónde:** `handoff.summarize_due` no reclama nada (dos workers resumen la misma conversación y se paga el modelo dos veces). `refresh_due` y `compact_due` eligen las mismas 20 filas sin `skip locked`: el segundo worker choca con el lock consultivo, saltea y no avanza con otras.
- **Impacto:** escalar horizontalmente (desde 1.000 negocios) no aumenta la capacidad y sí el gasto.
- **Arreglo:** reclamar con `update ... where id = (select ... for update skip locked) returning`, como ya hacen OCR y webhooks. **Esfuerzo: S.**

**A5. El aislamiento entre negocios en el chat público y en el worker depende sólo del código.**
- **Dónde:** `backend/app/db.py:55-77`. `tenant_tx` fija `app.current_tenant`, pero la conexión es `postgres` (BYPASSRLS). Las políticas `tenant_isolation` no aplican. Hay 16 rutas con `tenant_tx` y 2 con `system_tx` en `main.py`, más todo el agente y el worker.
- **Evidencia:** la consulta con `postgres` ignora `tenant_isolation` (medido arriba). Hoy todas las consultas revisadas filtran por `tenant_id`, pero un solo olvido expone datos de otros negocios.
- **Impacto:** el riesgo crece con la superficie de código y la cantidad de negocios; no es un problema de carga.
- **Arreglo:** que `tenant_tx` haga `set local role` a un rol sin BYPASSRLS, con las políticas `tenant_isolation` ya existentes. Primero hay que corregir C2, para no pagar ese costo. Agregar también un test que recorra las tablas con `tenant_id` y compruebe que, con otro tenant, no se ven filas. **Esfuerzo: M.**

**A6. Alta de cuentas sin fricción: cada cuenta es un negocio con cupo de IA.**
- **Dónde:** el trigger `handle_new_user` (`0003_accounts.sql:130-148`). En local, `supabase/config.toml` tiene `enable_confirmations = false` y no tiene captcha. La nube no se revisó (no se tocó).
- **Impacto:** con 13 cuentas falsas y bots de chat con IPs rotativas (`ip-day=400` por IP, sin agrupar IPv6 por /64), se agota el tope global de IA (C1) y se llenan `conversations` y `messages`.
- **Arreglo:**
  - Confirmar el email y poner captcha (Turnstile) en el registro.
  - Cupo de IA chico hasta que el negocio publique la tienda o verifique un medio de pago.
  - Agrupar IPv6 por /64 en `client_ip`.

  Antes, confirmar en el dashboard la configuración de Auth del proyecto remoto. **Esfuerzo: S–M.**

**A7. El chat público crea una conversación nueva en cada mensaje sin `conversation_id`.**
- **Dónde:** `backend/app/main.py:979-1010` (`buyer_session.start`). El límite `conv-hour` sólo aplica con id, y `store-hour` sólo apaga la IA (`limits.py:108-115`).
- **Impacto:** un bot crea hasta 400 conversaciones por IP y por día en cualquier tienda. Eso son filas sin retención, y la bandeja y los tableros del negocio se ensucian y se vuelven lentos.
- **Arreglo:**
  - Un límite de conversaciones nuevas por IP y por tienda, por hora.
  - Que la conversación no se cree hasta el primer mensaje válido.
  - Retención de conversaciones vacías o abandonadas.

  **Esfuerzo: S.**

**A8. Sin retención: tablas que crecen para siempre.**
- **Tablas:** `messages`, `conversations`, `audit_events`, `opportunity_activity`, `stock_movements`, `payment_notifications`, `webhook_deliveries`, `llm_usage`, `handoff_events` y `payment_documents.content` (`bytea` de hasta 10 MiB, `documents/ocr.py:29`, hasta 10 por pedido).
  - `rate_limits` sí se limpia (`limits.py:72`).
- **Impacto:**
  - **1.000 negocios:** unos 10–30 GB por año sólo en mensajes y comprobantes; backups y `VACUUM` lentos y plan de Supabase más caro.
  - **10.000 negocios:** de cientos de GB a TB. Los comprobantes en `bytea` inflan la DB y los backups.
- **Arreglo:**
  1. Definir la política de retención por tabla (ya figura como pendiente en `docs/current-state.md`).
  2. Mover los originales a Supabase Storage privado.
  3. Particionar `messages` por mes desde los 1.000 negocios.

  **Esfuerzo: M** (L con el particionado).

**A9. Pool chico y sin `statement_timeout` ni `idle_in_transaction_session_timeout`.**
- **Dónde:** `backend/app/db.py:27-31` (`max_size=10`, sin `timeout` explícito; psycopg_pool espera 30 s). Ninguna migración ni el código fijan timeouts de sentencia.
- **Evidencia:**
  - Las rutas síncronas de FastAPI corren en un pool de unos 40 hilos, más que las 10 conexiones.
  - Un turno de chat abre muchas transacciones cortas en serie: `ensure_conversation`, `add_message`, `_load_state`, perfil, nombre, resumen, historial, carrito, pedidos y uso de IA. Se estimaron 15–25 leyendo el código; no se midió.
  - `/health` abre una conexión nueva sin pool (`db.py:39-48`).
- **Impacto:** **100:** bien con 1–2 instancias. **1.000:** con N instancias × 10 conexiones se pasa el límite de conexiones directas de Supabase. **10.000:** hace falta sí o sí el pooler de transacción (pgbouncer o Supavisor en modo transacción). Ojo: ese modo exige que `set_config(..., true)` y `set local` vivan dentro de la transacción, que es lo que ya se hace.
- **Arreglo:**
  - `statement_timeout` (p. ej. 5 s en el panel y en el chat) e `idle_in_transaction_session_timeout` (p. ej. 30 s) por rol.
  - Usar el pooler de transacción en la nube y dimensionar `instancias × max_size`.
  - `/health` con el pool.

  **Esfuerzo: S.**

### MEDIOS

**M1. N+1 en `orders._view`.**
- **Dónde:** `backend/app/domain/orders.py:78-110`. Hace 4 consultas por pedido (pagos, constancia, calificación e ítems). Lo usa `backoffice.list_orders` (`domain/backoffice.py:278-282`) con `limit 100`: **unas 401 consultas** para abrir Pedidos.
- **Impacto:** hacia una DB remota (1–5 ms de ida y vuelta) son 0,4–2 s por carga, y empeora con C2.
- **Arreglo:** una sola consulta con `left join lateral` para el último pago, `json_agg` de ítems y joins a `receipts` y `order_ratings`. **Esfuerzo: S.**

**M2. La bandeja no corta por el `limit`.**
- **Dónde:** `backend/app/domain/inbox.py:44-64`. Hace un lateral por cada conversación del negocio y después ordena (62 ms con 20k conversaciones; lineal).
- **Arreglo:** una columna `conversations.last_message_at` que se actualice al insertar mensajes, con un índice `(tenant_id, last_message_at desc)`. **Esfuerzo: S.**

**M3. `insights.summary` usa subconsultas por día con `(created_at at time zone …)::date = g`.**
- **Dónde:** `backend/app/domain/insights.py:64-77`. No puede usar índices y recorre el período 30 veces. Además hay muchos `exists` sobre `messages` por conversación.
- **Impacto:** con negocios grandes y RLS (C2), es el tablero más lento.
- **Arreglo:** agrupar una sola vez por día (`group by date_trunc`) y cachear por negocio unos 5 minutos (la clave incluye el `tenant` y los `days`). **Esfuerzo: S.**

**M4. Georef sin caché negativa, con hasta 3 llamadas en serie y caché por proceso.**
- **Dónde:** `backend/app/domain/georef.py:43-70` y `:105-131`. `address` prueba hasta 3 variantes con 3 s cada una, sin caché. Si Georef se cae, cada mensaje de entrega paga hasta 3–9 s.
- **Impacto:** depende del tráfico de la API pública de datos.gob.ar, cuyo cupo no se verificó. Desde 1.000 negocios es probable que limite.
- **Arreglo:**
  - Caché compartida (tabla), también para las respuestas vacías y los errores durante unos minutos.
  - Un circuit breaker: tras N fallas seguidas, saltear Georef durante 60 s.

  **Esfuerzo: S.**

**M5. Mercado Pago dentro de una transacción con el pedido bloqueado.**
- **Dónde:** `backend/app/payments/service.py:50-73`. `create_checkout` (timeout de 15 s) corre con `for update` sobre el pedido y una conexión del pool tomada. Además, `get_provider()` crea un `httpx.Client` por llamada y nunca lo cierra (`providers.py:139`), así que no reutiliza conexiones.
- **Impacto:** si Mercado Pago anda lento, las conexiones del pool se agotan y se cae el chat.
- **Arreglo:** un cliente HTTP compartido y reclamar el cobro con una fila «creando» para llamar a Mercado Pago fuera de la transacción, o timeouts de 5 s. **Esfuerzo: S–M.**

**M6. Los pagos dependen del webhook; no hay conciliación.**
- **Dónde:** `payments/service.py:77-117`. Si Mercado Pago pierde el aviso o el backend estuvo caído más que sus reintentos, el pedido vence (`expire_reservations`) aunque esté cobrado.
- **Arreglo:** un job que consulte en Mercado Pago los pagos de pedidos `PENDING_PAYMENT` con preferencia antes de vencerlos. **Esfuerzo: M.**

**M7. `/health` informa `"live"` con `LLM_PROVIDER=openai`, pero ese planner no existe.**
- **Dónde:** `config.py:107-111` contra `agent/llm_sales.py:181-184`, que sólo implementa Ollama. Con OpenAI, el agente responde por reglas (`mode:"mock"` en el chat, que está bien), pero `/health` dice `live`.
- **Impacto:** observabilidad engañosa; roza la regla de honestidad («nunca fingir modelo real»).
- **Arreglo:** que `llm_is_live` refleje sólo los proveedores implementados. **Esfuerzo: S.**

**M8. Los tokens sólo se registran con los campos de Ollama.**
- **Dónde:** `domain/ai_usage.py:33-50` (`prompt_eval_count` y `eval_count`). Al sumar otro proveedor, los tokens quedarían en 0 y los topes por tokens no actuarían nunca.
- **Arreglo:** normalizar `usage.prompt_tokens/completion_tokens` al agregar proveedores. **Esfuerzo: S.**

### BAJOS

- **B1.** Búsqueda de catálogo con `LIKE '%kw%'` (`domain/inventory.py:133`, `domain/catalog.py:50`): recorre el catálogo del negocio. Con catálogos de menos de 10k productos está bien; si crecen, conviene un índice trigram (`pg_trgm`). **S.**
- **B2.** CORS `*` (`main.py:66-72`). La autenticación es Bearer y no hay cookies, así que el riesgo es bajo, pero conviene una lista de orígenes antes de producción. **S.**
- **B3.** Los contadores de `rate_limits` hacen 3 o 4 upserts por mensaje del chat, y el cubo `store-hour` de un negocio muy activo es una fila caliente. Está bien hasta 1.000 negocios; después conviene Redis o contadores en memoria con descarga periódica. **M.**
- **B4.** El OCR (onnxruntime) corre dentro del worker de mantenimiento: compite por CPU con todo lo demás. Desde 1.000 negocios, separarlo. **S.**

---

## Observabilidad: qué falta

- **Sin métricas ni trazas:** no hay Prometheus, OpenTelemetry ni Sentry (`backend/pyproject.toml`). No se sabe la latencia p95 del chat, el tiempo de cada vuelta del worker, la cola por tarea ni el uso del pool.
- **Sin id de request:** los logs de un turno (planner, controles, uso de IA) no se pueden juntar entre sí.
- **El worker sólo loguea un diccionario de conteos por vuelta**, sin duración ni atraso de las colas (antigüedad del pendiente más viejo de webhooks, memoria, planillas y comprobantes).
- **Alertas mínimas que faltan:**
  - tope global de IA superior al 70 %;
  - vuelta del worker de más de 2 min;
  - reservas vencidas sin liberar hace más de 5 min;
  - webhooks pendientes de más de 1 h;
  - pool sin conexiones libres;
  - tasa de 429 por tienda;
  - Georef y Mercado Pago con errores.
- **Arreglo:** logs JSON con `request_id`, `tenant_id` (no PII) y duración, más OpenTelemetry (FastAPI, psycopg y httpx) hacia un backend gratuito (Grafana Cloud o similar), y métricas del worker. **Esfuerzo: M.**

---

## Costo de IA por negocio y por mes

**Supuestos** (no hay telemetría real: hay que confirmarlos con `llm_usage` del piloto):
- un turno es 1 llamada con herramientas más 1 de redacción, con un 10 % de reescrituras: ~2,3 llamadas;
- 8 turnos por conversación, o sea ~18 llamadas;
- ~4.000 tokens de entrada por llamada (sistema, perfil, herramientas, contexto y 16 mensajes de historial) y ~250 de salida;
- en segundo plano, 1 destilado de memoria (~2k de entrada y 200 de salida) y, a veces, un resumen;
- **total: ~76k tokens de entrada y ~5k de salida por conversación.**

Los precios son de dos escenarios **hipotéticos**, porque el repo no fija proveedor (sólo Ollama está implementado):
- **Económico:** US$ 0,15 / 0,60 por millón de tokens (los valores de ejemplo de `.env.example`). Da unos **US$ 0,014 por conversación**.
- **Intermedio:** US$ 1 / 4 por millón. Da unos **US$ 0,10 por conversación**.

| Negocio | Conv./mes | Tokens/mes | Económico | Intermedio | ¿Entra en el tope por negocio (3 M tokens/día ≈ 37 conv/día)? |
|---|---|---|---|---|---|
| Chico | 300 | ~24 M | ~US$ 4 | ~US$ 30 | Sí |
| Mediano | 1.500 | ~120 M | ~US$ 21 | ~US$ 150 | En días pico, no |
| Grande | 6.000 | ~490 M | ~US$ 85 | ~US$ 600 | No: pasa a reglas desde la conversación ~37 de cada día |

| Plataforma | Conv./día (mezcla 80 % chico, 15 % mediano, 5 % grande) | Tokens/día | ¿Entra en el tope global (40 M/día)? |
|---|---|---|---|
| 100 negocios | ~1.800 | ~145 M | **No** (3,6×) |
| 1.000 negocios | ~18.000 | ~1.450 M | **No** (36×) |
| 10.000 negocios | ~180.000 | ~14.500 M | **No** (360×) |

**¿Alcanzan los topes de `limits.py`?** Como freno anti-abuso por negocio, sí. Como modelo de negocio, **no**:
- el tope global está fijo y no reparte (C1);
- el tope por negocio no depende del plan;
- es «blando», porque se cachea 5 s por proceso y el uso se registra después de la llamada; con N instancias, el exceso es de hasta N × turnos en curso × 6 llamadas.

**Palancas de costo:**
- caché de prompt del proveedor: el sistema y las herramientas son ~70 % del input y se repiten;
- bajar `HISTORY` cuando ya hay resumen;
- no redactar con el modelo las respuestas que son textuales (ya se hace con `_VERBATIM`).

## Latencia por conversación

Hasta 5 pasos del planner más 1 reescritura, con 60 s de timeout cada uno (`llm_sales.py:40` y `config.py:41`): **en el peor caso, unos 6 minutos de un hilo por mensaje**. Con unos 40 hilos por proceso, se atienden unos 40 chats en simultáneo por instancia; con Ollama (`qwen3:4b`), el cuello es el propio modelo. **Arreglo:** un tiempo total por turno (p. ej. 25 s) que, al vencer, siga por reglas, y pasar el chat a async o a una cola si se superan los 1.000 negocios.

---

## Plan priorizado

| # | Qué | Hallazgos | Esfuerzo | Cuándo |
|---|---|---|---|---|
| 1 | Políticas RLS con `(select app_member_tenant())`, sin `OR` con `tenant_isolation`; medir antes y después | C2 | S | Ya, antes del piloto |
| 2 | Topes de IA: global como freno de emergencia que escala; cupo por negocio según plan; cupo chico para cuentas nuevas | C1, A6 | M | Ya |
| 3 | Worker: `budget_s` en tareas de IA, `try` por tarea y por elemento, reservas en un bucle aparte | C3 | S | Ya |
| 4 | Sacar las llamadas al modelo de las transacciones (memoria, compactación) y reclamar con `skip locked` (resúmenes) | C4, A4 | S–M | Ya |
| 5 | `statement_timeout` e `idle_in_transaction_session_timeout`; pooler de transacción en la nube | A9 | S | Antes del piloto |
| 6 | Índice y resumen de `llm_usage` por día; contador de mensajes para `compact_due`; índice parcial para evals | A1, A2 | S–M | Antes de 100 negocios |
| 7 | Captcha, confirmación de email, límite de conversaciones nuevas por IP y agrupación IPv6 /64 | A6, A7 | S | Antes de abrir el registro |
| 8 | Observabilidad: `request_id`, logs JSON, OpenTelemetry, métricas y alertas del worker | Obs. | M | Antes de 100 negocios |
| 9 | N+1 de pedidos, bandeja con `last_message_at`, tablero agrupado y cacheado | M1–M3 | S | Antes de 100 negocios |
| 10 | Mercado Pago por negocio (OAuth) y conciliación de pagos | C5, M6 | L | Antes del primer cobro real |
| 11 | Retención por tabla y comprobantes en Storage | A8 | M | Antes de 1.000 negocios |
| 12 | Reparto justo en el worker (webhooks, planillas) y circuit breakers (Georef, webhooks) | A3, M4 | M | Antes de 1.000 negocios |
| 13 | Rol sin BYPASSRLS en `tenant_tx` y test de aislamiento por tabla | A5 | M | Antes de 1.000 negocios |
| 14 | Separar los workers (IA, OCR, mantenimiento), chat async o en cola, particionar `messages` | C3, B4, A8 | L | Antes de 10.000 negocios |

**Qué se rompe primero:**
- **Con 100 negocios:** el tope global de IA (C1), el panel lento en los negocios más grandes (C2) y un worker frágil ante un modelo lento (C3).
- **Con 1.000 negocios:** además, las conexiones (C4, A9), los atrasos de planillas y webhooks (A3), `ai_allowed` y `compact_due` caros (A1, A2), la falta de observabilidad y el crecimiento de la DB (A8).
- **Con 10.000 negocios:** la arquitectura de un único worker en serie y del chat síncrono, además de todo lo anterior.
