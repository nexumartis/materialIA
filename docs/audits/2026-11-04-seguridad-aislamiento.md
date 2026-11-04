# Auditoría de seguridad: aislamiento entre negocios y abuso a escala — 04/11/2026

Revisión **de sólo lectura** sobre `main` (`6ea7968`). No se tocó código, nube ni secretos. Las
vulnerabilidades se describen como clases y lugares, sin pasos de explotación. La tabla de RLS sale
del catálogo de la base de pytest local (`127.0.0.1:55436`, migraciones 0001–0026). El remoto no se
consultó, así que puede diferir.

## Resumen (5 líneas)

1. El panel (`/app/*`) está bien armado: el negocio sale del JWT verificado más `memberships`, y casi todo corre en `user_tx` con RLS real (`app_user`, sin BYPASSRLS).
2. Pero el chat público, el agente, los pagos, el worker y varias rutas del panel corren con `tenant_tx`/`system_tx`, que se conectan como `postgres` (**BYPASSRLS**). Ahí el aislamiento depende sólo de que cada query tenga su `where tenant_id = …`. No encontré ninguna query que lo omita en un camino explotable, pero no hay red de seguridad.
3. Con miles de negocios, el riesgo principal no es un IDOR: es el **abuso compartido**. Hay un tope global de IA que unos pocos negocios (o cuentas creadas en masa, con registro abierto y sin confirmar email) pueden agotar para todos, un worker único y en serie, y límites por IP fáciles de rotar.
4. Configuración riesgosa por defecto fuera de local: CORS `*`, `PAYMENT_PROVIDER=simulated` con una clave de firma pública, rutas `/sandbox/*` de lectura y chat siempre activas, y emails sin confirmar (eso último habilita entrar a un equipo ajeno con una invitación).
5. Privacidad: no hay retención ni borrado automático de mensajes, contactos de entrega, comprobantes (`bytea`) ni payloads de webhooks; además, el webhook manda el teléfono del comprador aunque su docstring dice lo contrario.

Tests: 461 passed, 0 failed contra la base local (ver «Evidencia» al final).

---

## Hallazgos por severidad

Esfuerzo: **S** = horas, **M** = 1–3 días, **L** = una semana o más.

### Crítico

No encontré ninguna fuga directa entre negocios (IDOR) explotable hoy. Todas las rutas que reciben
un id (pedido, conversación, documento, endpoint, turno, versión) lo cruzan con el negocio resuelto
en el servidor.

### Alto

**A1. El backend no tiene RLS efectivo: `tenant_tx`/`system_tx` corren como `postgres` con BYPASSRLS.**
- **Dónde:** `backend/app/db.py:50-75` (`tenant_tx` sólo fija `app.current_tenant`, sin `set local role`). En el catálogo, `postgres` tiene `rolbypassrls = t` y ninguna tabla tiene `FORCE ROW LEVEL SECURITY`. Las políticas `tenant_isolation` de 0001/0004/0007/0008/0009/0011/0013 no aplican nunca a esas conexiones.
- **Lo usan:** el chat público y el agente (`agent/sales_agent.py`, `llm_sales.py`), pagos (`payments/service.py`), `buyer_session.py`, `customer_memory.py`, `documents/store.py`, el worker y también rutas del panel que salen de `user_tx` a `tenant_tx` (`main.py:664,684,726-820,838,848,1057,1077,1100`).
- **Por qué importa con muchos negocios:** un solo `where` olvidado en un cambio futuro (y hay decenas de queries a mano) expone datos de todos los negocios. Además, el LLM con herramientas corre exactamente en esta capa. Hoy la protección es la disciplina de código, no la base. Ejemplo de estilo frágil: `customer_memory.py:172` filtra sólo por `customer_id` (que es PK y sale de la base, así que no es explotable, pero es el patrón a evitar).
- **Arreglo:** crear un rol `app_backend` NOBYPASSRLS y hacer que `tenant_tx` ejecute `set local role app_backend`, con políticas `tenant_isolation ... to app_backend` (la GUC ya existe). Dejar `system_tx` (BYPASSRLS) sólo para el worker y los webhooks, con una lista cerrada de queries. Sumar un test que recorra todas las tablas con `tenant_id` y compruebe que, con otro tenant fijado, devuelven 0 filas. **M/L**.

**A2. Tope global de IA compartido + registro abierto ⇒ un actor deja sin IA a todos los negocios.**
- **Dónde:** `backend/app/config.py:58-61` (1.500 llamadas por negocio y 20.000 globales por día) y `domain/limits.py:125-160` (`ai_allowed`). Con 14 negocios al tope por negocio ya se llega al global. Registrarse crea un negocio al instante (`supabase/migrations/0016_team.sql:42-58`, `handle_new_user`), sin captcha (`supabase/config.toml:213`) y con `enable_confirmations = false` (`config.toml:226`, local; confirmar el remoto).
- **Por qué importa:** con miles de negocios, el tope global es un punto único de falla. Cualquiera que cree cuentas, o un par de tiendas con mucho tráfico (incluso bots contra su chat público), apaga la IA de todo el mundo hasta el día siguiente. El negocio sigue vendiendo en modo `mock`, pero no lo eligió.
- **Arreglo:** que el tope global sea una alarma y un corte duro sólo en el proveedor, no un corte para todos. Topes por negocio según plan. Confirmación de email y captcha en el registro, más un límite de negocios nuevos por IP/día. Negocios nuevos con un tope bajo hasta verificarlos. **M**.

**A3. Invitaciones de equipo sin email confirmado ⇒ entrar al negocio ajeno como staff.**
- **Dónde:** `0016_team.sql:42-58` y `:63-72`. El ingreso exige `email_confirmed_at`, pero con `enable_confirmations = false` Supabase confirma el email en el alta. Quien se registre primero con un email invitado entra como staff: ve bandeja, mensajes, pedidos, contactos de entrega y comprobantes.
- **Por qué importa:** el control depende de una opción del proyecto remoto que el código no verifica. A escala, alguna invitación a un email adivinable (ventas@, info@) va a pasar.
- **Arreglo:** exigir confirmaciones en el remoto y verificarlo al arrancar o en un test. Mejor aún, que la invitación lleve un token de un solo uso que el invitado presente (no sólo el email), con vencimiento. **S** (config) / **M** (token).

**A4. Valores por defecto inseguros fuera de local (CORS `*`, pago simulado, sandbox abierto).**
- **Dónde:**
  - `main.py:66-72`: `allow_origins=["*"]`.
  - `config.py:73,80`: `payment_provider="simulated"` y `sim_webhook_secret` fija y pública.
  - `main.py:245-272`: el checkout simulado marca pedidos PAID sin plata, para cualquiera que tenga el link.
  - `main.py:108-197`: `/sandbox/products`, `/sandbox/opportunities`, `/sandbox/sales/chat`, `/sandbox/sales/{id}` y `/sandbox/orders/{id}` no dependen de `APP_ENV`.
- **Por qué importa:** si un despliegue olvida una variable, quedan pedidos «pagados» sin cobro (rompe la invariante de honestidad), el chat del sandbox gasta IA y el CORS abierto amplía la superficie del panel (hoy usa bearer y no cookies, lo que mitiga CSRF).
- **Arreglo:** al arrancar con `APP_ENV != local`, fallar si `payment_provider == simulated`, si `sim_webhook_secret` es el valor por defecto o si CORS no tiene una lista explícita. Montar `/sandbox/*` sólo en local. **S**.

### Medio

**M1. Límites del chat público evitables y con huecos.**
- `limits.py:99-122`: el límite por IP no agrupa IPv6 por /64 ni ASN, así que rotando IPs se evita.
- `limits.py:43-63`: si la base falla, los contadores dejan pasar (fail-open).
- Si `trusted_proxy_hops = 0` detrás de un proxy (`config.py:64`), todos los clientes comparten una sola IP y se bloquean entre sí.
- Rutas públicas sin límite: `GET /public/{slug}` (`main.py:947`), `GET /public/{slug}/conversations/{id}` (`:1005`), `cancel` (`:1050`), `receipts/{id}/pdf` (`:1093`, que renderiza un PDF en cada pedido), `DELETE /public/{slug}/me` (`:995`) y `POST /webhooks/{provider}` (`:275`; los avisos con firma inválida no escriben nada, pero cada uno igual cuesta parsear y verificar).
- `store-hour` pasa la tienda a modo sin IA (`limits.py:118-122`): un tercero puede degradar la tienda de un competidor durante una hora.
- **Arreglo:** agrupar por /64, aplicar el límite a todas las rutas públicas, un WAF o captcha suave tras N conversaciones nuevas por IP y alertar cuando una tienda se degrada. **M**.

**M2. Acciones del panel que gastan IA sin `guard_user`.**
- `PUT /app/agent-profile` con `require_evals` corre todas las evaluaciones (`main.py:442-449`) sin límite.
- `POST /app/knowledge` calcula embeddings de hasta 200 mil caracteres (`main.py:1111-1121`, `knowledge.py:24`) sin límite.
- `POST /app/inbox/{id}/quote` y la sincronización de la planilla (`main.py:535`) tampoco tienen límite.
- **Arreglo:** pasar `guard_user` con peso por caso o por fragmento. **S**.

**M3. Worker único y en serie: el vecino ruidoso frena a todos.**
- `worker.py:28-37`, `webhooks.py:167-210` (de a uno, 5 s de timeout, 30 s de presupuesto), `customer_memory.refresh_due(limit=20)`, OCR y compactación en la misma vuelta.
- Con miles de negocios, unos pocos endpoints lentos o un pico de memoria o OCR atrasan los webhooks, los vencimientos de reserva y la lectura de comprobantes de todos.
- **Arreglo:** colas separadas por tarea, cupo por negocio en cada vuelta, concurrencia acotada para los webhooks y desactivar un endpoint tras N fallas. **M**.

**M4. Una sola cuenta de Mercado Pago para toda la plataforma.**
- `providers.py:144-150` usa `settings.mp_access_token` global, y `notification_url` y `MP_WEBHOOK_SECRET` también son comunes.
- La plata de todos los negocios cae en una cuenta y el negocio del pago se deriva del `external_reference` (el pedido). Está bien validado (monto, moneda y pedido real, `service.py:122-150`), pero es un riesgo regulatorio y de concentración: un secreto filtrado afecta a todos.
- **Arreglo:** OAuth de MP por negocio (marketplace o cuenta propia), con el token cifrado y guardado por negocio. **L**.

**M5. Sin retención ni borrado de datos personales.**
- `messages`, `conversations.summary`, `orders.delivery_contact` y `delivery_address`, `payment_documents` (original en `bytea`), `webhook_deliveries.payload`, `conversation_notes` y `audit_events` no tienen TTL. El worker no purga nada salvo `rate_limits`, previews y memoria.
- «Olvidarme» (`customer_memory.py:108-121`) borra la memoria, pero deja mensajes, contacto de entrega y comprobantes.
- No hay borrado de un negocio completo (baja de cuenta) ni exportación.
- **Por qué importa:** con miles de negocios, el volumen de PII crece sin límite y no hay forma de cumplir una solicitud de supresión (Ley 25.326).
- **Arreglo:** política de retención por tabla (por ejemplo, mensajes 12–24 meses, comprobantes según la obligación contable), un job de purga, borrado de un negocio en cascada y una exportación. **M**.

**M6. El webhook saliente manda el contacto del comprador, y la docstring dice que no.**
- `webhooks.py:15-16` dice «nunca teléfonos», pero `enqueue_order` (`webhooks.py:133-137`) incluye `delivery_contact` (nombre y teléfono) y la dirección. Además, el payload queda guardado en `webhook_deliveries` sin vencimiento.
- **Arreglo:** decidir si va o no. Si va, documentarlo, avisarle al dueño y purgar los payloads enviados. **S**.

**M7. Enumeración de tiendas y de cuentas.**
- Slug por defecto = nombre + 4 hex (`agent_profile.py:156`) ⇒ 65.536 opciones por nombre. Con `GET /public/{slug}` sin límite, se puede listar qué negocios usan la plataforma.
- `team.invite` (`team.py:44-51`) dice si un email ya tiene cuenta o una invitación de otro negocio, lo que permite enumerar usuarios. Además, un negocio puede «reservar» emails ajenos (la PK es global) y bloquear invitaciones de otros, sin tope de invitaciones.
- **Arreglo:** sufijo aleatorio más largo, limitar `/public/{slug}`, mensaje genérico en la invitación, tope de invitaciones pendientes por negocio y vencimiento. **S**.

**M8. Defensa en profundidad de la Data API de Supabase.**
- `anon` y `authenticated` conservan **todos** los privilegios de tabla (los grants por defecto de Supabase) en 14 tablas: `tenants`, `memberships`, `conversations`, `messages`, `opportunities`, `catalog_items`, `price_entries`, `demo_customers`, `audit_events`, `conversation_notes`, `order_ratings`, `quick_replies`, `handoff_events` y `appointments`. Hoy no ven filas porque RLS está activo y sus políticas son `to app_user` o dependen de una GUC que PostgREST no fija. Pero la clave anon es pública en el front y basta una política nueva sin `to app_user`, o un `disable rls`, para exponerlas.
- **Arreglo:** una migración idempotente con `revoke all on <tablas> from anon, authenticated` y default privileges revocados en `public`, o sacar `public` de `[api].schemas`. **S**.

### Bajo

- **B1. Inyección de prompt.** El texto del comprador, del documento de conocimiento, de la web del negocio y del PDF entra al modelo. Lo mitiga que las herramientas tomen el negocio de `ToolContext` (`agent/tools.py`), que precios y stock salgan de la base y que el pago sólo se acredite verificado. El riesgo que queda: que el agente filtre a un comprador el perfil, las reglas o el contenido de la base de conocimiento del negocio (información interna del mismo negocio) o que prometa cosas en el texto. Arreglo: no poner datos internos en la base de conocimiento visible y testear con evaluaciones adversariales. **S/M**.
- **B2. Mismo origen para el panel y la tienda pública/widget.** `web/public/widget.js` abre `base/?embed=1#/tienda/slug`, del mismo origen que el panel, donde supabase-js guarda el JWT en `localStorage`. Un XSS en la tienda (texto del LLM, nombres de productos) llegaría a la sesión del dueño. No hay `dangerouslySetInnerHTML` en `web/src`, lo cual está bien. Tampoco vi CSP ni `frame-ancestors` para el panel (riesgo de clickjacking). Arreglo: servir la tienda desde otro subdominio, más CSP y `frame-ancestors 'none'` en el panel. **M**.
- **B3. El bloqueo de un contacto se evade abriendo una conversación nueva sin `X-Buyer-Key`** (`privacy.py:107-115`). Es esperable sin identidad fuerte. Documentarlo.
- **B4. SSRF bien resuelto** (`domain/safe_http.py`): verifica todas las IPs, fija la IP, no sigue redirecciones en webhooks y valida cada salto en `agent_suggest`. La planilla usa un allowlist de Google. Quedan pendientes: `agent_suggest` permite `http` y cualquier puerto público (escaneo de puertos de terceros desde nuestra IP) y no hay límite de tamaño total en tiempo. Arreglo: puertos 80/443 solamente. **S**.
- **B5. Errores y detalle.** `/health` expone `app_env`, el modelo y el proveedor de pagos. Varias rutas devuelven `str(exc)` de un `ValueError` al cliente (`main.py:139,209,…`). Revisar que ningún `ValueError` de la librería lleve datos internos. **S**.
- **B6. Seguridad de las contraseñas.** `minimum_password_length = 6` y sin requisitos (`config.toml:182-185`). Para cuentas que manejan pagos y PII: 10+ caracteres y verificación contra contraseñas filtradas. **S**.

### Lo que está bien (para no romperlo)

- JWT verificado con JWKS asimétrico, `aud`, `iss`, `exp` y `sub` UUID (`auth.py`), y negocio derivado de `memberships` con `app_member_tenant()` security definer.
- Token del comprador: 256 bits, guardado como hash, en header y no en la URL; misma respuesta 404 para algo inexistente o ajeno (`buyer_session.py`).
- Firma HMAC de Mercado Pago con `compare_digest` y el estado del pago siempre consultado al proveedor. Los webhooks salientes van firmados con timestamp.
- Carga de comprobantes: verifica la conversación antes de leer el cuerpo, corta el stream por tamaño, valida tipo y magic bytes, limita por pedido y desduplica por negocio.
- Rol del panel `app_user` con grants por columna (por ejemplo, sin `access_token_hash`).

---

## Cobertura de RLS por tabla (base local de pytest, 0001–0026)

Leyenda:
- `TI` = `tenant_isolation` (sin rol, GUC `app.current_tenant`; **no aplica al backend, que tiene BYPASSRLS**).
- `MA`/`MO` = `member_access` (permisiva) / `member_only` (restrictiva), `to app_user`.
- «anon/auth ALL» = `anon` y `authenticated` tienen todos los privilegios de tabla (sólo los frena RLS).

Ninguna tabla tiene `FORCE RLS`.

| Tabla | RLS | Políticas | `app_user` | anon/auth | Nota |
|---|---|---|---|---|---|
| tenants | sí | MA(sel), MO | SELECT | **ALL** | M8 |
| memberships | sí | MA(sel), MO | SELECT | **ALL** | M8 |
| catalog_items | sí | TI, MA, MO | SEL/INS/UPD | **ALL** | M8 |
| price_entries | sí | TI, MA, MO | SEL/INS/UPD | **ALL** | M8 |
| demo_customers (clientes) | sí | TI | — | **ALL** | PII; sin política para el panel |
| conversations | sí | TI, MA, MO | por columnas (sin token) | **ALL** | M8 |
| messages | sí | TI, MA, MO | SEL/INS | **ALL** | PII sin retención |
| opportunities | sí | TI, MA, MO | SEL/UPD | **ALL** | M8 |
| opportunity_activity | sí | TI, MA, MO | SEL/INS | **ALL** | M8 |
| audit_events | sí | MA(ins), MO | INS | **ALL** | M8 |
| stock_levels | sí | TI, MA, MO | SEL/INS/UPD | — | |
| stock_movements | sí | TI, MA, MO | SEL/INS | — | |
| orders | sí | TI, MA, MO | SEL/UPD | — | `delivery_contact` PII |
| order_items | sí | TI, MA, MO | SEL | — | |
| payments | sí | TI, MA, MO | SEL | — | |
| payment_notifications | sí | (ninguna) | — | — | sólo backend |
| sim_provider_payments | sí | (ninguna) | — | — | sólo backend |
| agent_profiles | sí | MA, MO | SEL/INS/UPD | — | |
| agent_profile_versions | sí | TI, MA, MO | SEL/INS | — | |
| customer_identities | sí | TI | — | — | sólo backend |
| customer_memory | sí | TI | — | — | PII derivada |
| knowledge_documents | sí | TI, MA, MO | SEL/INS/DEL | — | |
| knowledge_chunks | sí | TI, MA, MO | SEL/INS/DEL | — | |
| agent_eval_cases | sí | TI, MA, MO | SEL/INS/DEL | — | |
| receipts | sí | TI, MA, MO | SEL | — | |
| payment_documents | sí | TI, MA, MO | SEL, UPD(decisión) | — | original `bytea` |
| catalog_sources | sí | TI, MA, MO | SEL/INS/UPD/DEL | — | |
| llm_usage | sí | TI, MA(sel), MO(sel) | SEL | — | |
| team_invites | sí | (ninguna) | — | — | sólo backend |
| conversation_notes | sí | MA, MO (autor = uid) | SEL/INS | **ALL** | M8 |
| rate_limits | sí | (ninguna) | — | — | sólo backend |
| order_ratings | sí | MA(sel), MO | SEL | **ALL** | M8 |
| webhook_endpoints | sí | MA(sel), MO | SEL por columnas (sin secreto) | — | |
| webhook_deliveries | sí | MA(ins), MO | INS | — | payload con PII (M6) |
| handoff_events | sí | MA, MO | SEL, UPD(columnas) | **ALL** | M8 |
| quick_replies | sí | MA(sel), MO | SEL | **ALL** | M8 |
| appointments | sí | MA, MO | SEL, UPD(columnas) | **ALL** | M8 |

Funciones `security definer` (`app_member_tenant`, `app_member_role`, `app_join_invited`,
`handle_new_user`, `handle_user_confirmed`): todas con `search_path` fijo y `EXECUTE` revocado a
`public`, `anon` y `authenticated`. Bien.

## Rutas: de dónde sale el negocio

- **`/app/*`** (≈60 rutas): siempre de `current_uid` (JWT) más `memberships`. Las de plata, catálogo, configuración y equipo pasan por `owner_uid`. Las que después abren `tenant_tx` usan el negocio que devolvió `user_tx`, nunca uno del cliente.
- **`/public/{slug}/*`**: del slug resuelto en el servidor más el token de conversación (`_owned`) en cada lectura y escritura. `GET /public/{slug}` y `DELETE /me` no piden token (no exponen datos de la conversación).
- **`/sandbox/*`**: de un allowlist fijo C/D; excluye las conversaciones públicas. Ver A4.
- **`/webhooks/{provider}` y `/sandbox/checkout/*`**: del pedido referenciado en la base (`_order_tenant`, `system_tx`), nunca del cuerpo.

## Plan priorizado

1. **Esta semana (S):**
   - A4: guardas de arranque fuera de local (pago simulado, secreto, CORS, `/sandbox/*` sólo en local).
   - A3: confirmar email obligatorio en el remoto y un test que lo verifique.
   - M8: revocar anon/authenticated.
   - M2: `guard_user` en evaluaciones, conocimiento, cotización y planilla.
   - M6: decidir y documentar el contacto en webhooks.
2. **Antes de abrir el registro a terceros (M):**
   - A2: topes por negocio y por plan, captcha y confirmación, límite de altas por IP, y que el tope global sólo alerte.
   - M1: límites en todas las rutas públicas, /64.
   - M7.
   - B6.
3. **Antes del piloto con datos reales (M/L):**
   - A1: rol `app_backend` sin BYPASSRLS para `tenant_tx`, más un test de aislamiento por tabla.
   - M5: retención, purga, baja de negocio y exportación.
   - B2: tienda en otro origen, CSP y `frame-ancestors`.
4. **Al crecer (L):**
   - M3: colas por tarea con cupo por negocio.
   - M4: Mercado Pago por negocio (OAuth).

## Evidencia

- Catálogo leído de la base de pytest local: RLS, políticas, grants y roles (`postgres` y `service_role` con BYPASSRLS; `app_user`, `anon` y `authenticated` sin él).
- Tests: `DATABASE_URL=…55436 PV_REQUIRE_DB=1 pytest -q`. Resultado del 04/11/2026: **461 passed, 0 failed** en 39 s (2 warnings: un JWT HMAC corto de los tests). Los tests verdes no cubren los hallazgos de abuso y configuración de arriba.
