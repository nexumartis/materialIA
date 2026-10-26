# Agente de ventas end-to-end — diseño y plan por etapas

Fecha: 26/10/2026. Fuente: especificación "Agente de Ventas Autónomo por WhatsApp — Construcción y
Grifería" aportada por el socio (19 secciones). Este documento la contrasta con el código vigente,
fija decisiones y define la **primera entrega** implementada en `feat/sales-agent-commerce`.

## 1. Objetivo

Un vendedor digital que atiende de punta a punta: consulta → stock y precio reales → carrito →
pedido → link de pago → confirmación verificada → estado del pedido, todo desde el chat, con el CRM
actualizado. Primer rubro: grifería, sanitarios y ferretería. Canal final: WhatsApp e Instagram.

## 2. Qué se reutiliza del repo

| Pieza existente | Uso en el agente de ventas |
|---|---|
| FastAPI + psycopg + migraciones SQL (`supabase/migrations`) | Se mantiene como monolito modular. |
| `tenant_tx` / `user_tx`, RLS y cuentas (0003) | Todo lo nuevo filtra por tenant resuelto en servidor y lleva RLS. |
| `catalog_items` + `price_entries` (`fixed` / `custom_quote`) | Catálogo y precios. `fixed` se vende solo; `custom_quote` sigue derivando a una persona. |
| `conversations` / `messages` | Historial y bandeja de salida del canal simulado. |
| `opportunities` + timeline | Lead/CRM: la conversación de venta crea y avanza la oportunidad. |
| `tool_agent` (allowlist, tenant desde contexto) | Mismo contrato para las herramientas de venta. |

## 3. Decisiones (desvíos documentados respecto de la especificación)

- **D1 — Stack.** Se conserva el stack vigente: FastAPI + SQL plano versionado (CLAUDE.md prohíbe
  ORM: "una sola fuente de verdad = migraciones SQL"), Vite/React en vez de Next.js, Supabase local
  (`supabase start`, ya corre en Docker) en vez de un `docker-compose` propio. Cambiar a
  SQLAlchemy/Alembic/Next.js reescribiría lo que funciona sin aportar al objetivo.
- **D2 — Cola y worker sin Redis.** Las tareas persistentes viven en Postgres (estado en tablas,
  operaciones idempotentes) y un worker simple (`python -m app.worker`) las ejecuta en bucle. Redis
  se incorpora sólo si la carga lo justifica.
- **D3 — Canal.** El agente no depende del canal: recibe texto y devuelve texto. El canal de esta
  entrega es el **chat demo simulado**. WhatsApp/Instagram reales quedan bloqueados por la regla
  vigente "NO WhatsApp, NO envíos a clientes, NO producción en esta fase" hasta que los dos socios
  la cambien en CLAUDE.md.
- **D4 — Pagos.** Interfaz `PaymentProvider` con dos implementaciones:
  `simulated` (por defecto, sin credenciales; recorre el mismo camino de webhook y verificación) y
  `mercadopago` (Checkout Pro por API REST, activo sólo con `MP_ACCESS_TOKEN` de prueba). Una orden
  **sólo** pasa a pagada cuando el proveedor confirma el pago consultado por API; nunca por lo que
  diga el cliente. Todo resultado expone `mode` (`simulated` / `mercadopago`).
- **D5 — Stock consistente y concurrente.** Ver §5.
- **D6 — Confirmación.** Las escrituras comerciales irreversibles (generar el pedido y el link)
  requieren la confirmación explícita del cliente en el chat ("sí"), sobre un resumen con total. Las
  cotizaciones a medida siguen requiriendo a una persona del negocio.
- **D7 — Rubro.** Se agrega una tercera empresa demo **C (grifería)** con datos sintéticos y marcas
  ficticias. A y B (cerramientos) quedan intactas.
- **D8 — Variantes.** Cada variante (color, medida) es un SKU propio; la tabla de variantes llega si
  el catálogo real lo exige.
- **D9 — Un depósito.** Stock por empresa y producto; multi-depósito queda preparado (columna
  futura) pero fuera de esta entrega.

## 4. Modelo de datos (migración 0004)

- `catalog_items` + `brand`, `description`, `image_url`, `unit`.
- `conversations.agent_state jsonb`: memoria estructurada (últimos productos mostrados,
  confirmación pendiente). Evita "recordar" precios o stock: sólo IDs.
- `stock_levels(tenant_id, item_id, on_hand, reserved)` con `check (reserved <= on_hand)` y no
  negativos.
- `stock_movements`: historial inmutable de cada cambio (`restock`, `adjust`, `reserve`, `release`,
  `sale`).
- `orders`: `status` ∈ `CART_OPEN, PENDING_PAYMENT, PAID, PREPARING, DISPATCHED, IN_TRANSIT,
  DELIVERED, CANCELLED, REFUNDED`; totales; `reserved_until`; `attention_reason`; número visible.
  Un solo carrito abierto por conversación (índice único parcial).
- `order_items`: precio unitario visto por el cliente y total de línea; FK compuesta por tenant.
- `payments`: proveedor, modo, preferencia, link, id de pago del proveedor (único), estado, monto.
- `payment_notifications`: registro de cada aviso recibido (auditoría y depuración).
- `sim_provider_payments`: "servidor" del proveedor simulado.

## 5. Stock: consistencia bajo concurrencia

1. **Apartado atómico y condicional**:
   `update stock_levels set reserved = reserved + q where … and on_hand - reserved >= q`. Sin
   lectura previa; Postgres serializa las escrituras sobre la fila.
2. **Restricciones en la base** (`reserved <= on_hand`, no negativos): aunque haya un bug, no se
   vende de más.
3. **Pedidos con varios productos**: todo o nada en una transacción, bloqueando en orden de
   `item_id` para evitar deadlocks.
4. **Cuándo se aparta**: al confirmar la compra (pasa a `PENDING_PAYMENT`), con vencimiento
   (`RESERVATION_MINUTES`, 30 por defecto). El worker libera los vencidos (`CANCELLED`,
   `reservation_expired`).
5. **Pago confirmado**: descuenta `on_hand` y `reserved` una sola vez (transición
   `PENDING_PAYMENT → PAID` con la orden bloqueada). Avisos repetidos no tienen efecto.
6. **Pago tardío** (reserva vencida): se intenta apartar de nuevo; si no hay stock, la orden queda con
   `attention_reason = paid_without_stock` para devolución humana.
7. **Prueba de aceptación**: N compras concurrentes de la última unidad ⇒ exactamente una gana.
8. **Salvedad**: si el stock también se vende por fuera (mostrador u otra tienda) y se sincroniza,
   entre sincronizaciones puede haber sobreventa; se mitiga con margen de seguridad o confirmación
   humana. Se documenta en el conector.

## 6. Herramientas del agente de ventas (esta entrega)

| Herramienta | Tipo | Contrato |
|---|---|---|
| `buscar_productos` | lectura | texto libre, color, presupuesto máx. → productos activos con precio vigente y disponible |
| `consultar_stock` | lectura | producto → disponible real (`on_hand - reserved`) |
| `ver_carrito` | lectura | carrito abierto de la conversación con totales |
| `agregar_al_carrito` / `quitar_del_carrito` | escritura reversible | producto + cantidad; valida precio vigente y stock disponible (sin apartar) |
| `comprar` | escritura irreversible | revalida precios y stock, aparta, crea pedido `PENDING_PAYMENT` y link de pago; requiere "sí" del cliente |
| `estado_pedido` | lectura | pedidos de la conversación con estado y pago verificados |

Todas reciben el tenant del `ToolContext`. Referencias del cliente ("la primera", "esa negra")
se resuelven contra los IDs guardados en `agent_state`, nunca contra precios recordados.

El planner de esta entrega es **determinista** (modo `mock`, sin LLM): reconoce intención,
cantidades, color, presupuesto y ordinales en español rioplatense. El planner con LLM reutiliza las
mismas herramientas en una entrega posterior; nunca escribe respuestas con datos que no salgan de
una herramienta.

## 7. Etapas

| Etapa | Contenido | Estado |
|---|---|---|
| 1 | Catálogo extendido, stock concurrente, carrito, pedidos, seed grifería | **esta entrega** |
| 2 | Agente de ventas con herramientas + memoria por conversación (planner determinista) | **esta entrega** |
| 3 | Checkout, Mercado Pago (simulado + adaptador real de prueba), webhook verificado, worker de vencimientos | **esta entrega** |
| 3b | Planner con LLM sobre las mismas herramientas; panel de pedidos | siguiente |
| 4 | WhatsApp Cloud API real | requiere cambio de alcance acordado |
| 5 | CRM completo, envíos con interfaz de proveedor, toma de control humana | posterior |
| 6 | Recuperación de carritos y seguimientos programados | posterior (requiere canal real) |
| 7 | Staging, observabilidad, despliegue | posterior |

## 8. Criterios de aceptación de esta entrega

- **Escenario A (simulado)**: "¿tenés canillas negras para cocina?" → opciones reales con precio y
  disponible → "por menos de 100 mil" → "agregame la primera" → "la compro" → resumen y total →
  "sí" → link de pago (modo explícito) → pago aprobado en el checkout simulado → pedido `PAID`,
  stock descontado, oportunidad avanzada, mensaje de confirmación en la conversación.
- **Escenario B**: "¿ya salió mi pedido?" → estado real de la orden.
- **Escenario D**: producto agotado → no promete disponibilidad y ofrece alternativas reales.
- Concurrencia: 20 compras simultáneas de la última unidad ⇒ 1 pedido, 19 "sin stock".
- Aviso de pago repetido ⇒ un solo descuento de stock. "Ya pagué" del cliente ⇒ no cambia nada.
- Aislamiento: la empresa A no ve pedidos ni stock de C.

## 9. Riesgos y dependencias externas

- Mercado Pago real: requiere cuenta, `MP_ACCESS_TOKEN` de prueba, `MP_WEBHOOK_SECRET` y una URL
  pública para el webhook (túnel en desarrollo). La firma `x-signature` se implementa según la
  documentación pública; **no se verificó contra Mercado Pago real** en esta entrega.
- WhatsApp: cuenta de Meta Business, número verificado y plantillas aprobadas; cambio de alcance.
- Sin LLM en vivo la comprensión es por reglas: cubre los escenarios, no toda la variedad del
  lenguaje.
- Las migraciones 0002–0004 siguen sin aplicarse al Supabase remoto.

## 10. Mensajes interactivos y su traducción a WhatsApp

Cada respuesta del agente lleva, además del texto completo, un bloque `ui` independiente del
canal (se guarda en `messages.payload`). Cada botón **envía un mensaje de texto** que el agente
ya entiende ("agregame la 2", "comprar", "sí"), así el flujo es idéntico si el canal no soporta
botones y el cliente lo escribe a mano.

| Bloque `ui` | Chat web | WhatsApp Cloud API (dentro de la ventana de 24 h, sin plantilla) |
|---|---|---|
| `products` (foto, nombre, precio, stock, acción) | Tarjetas con foto; tocar abre el detalle | Mensajes de imagen con texto + mensaje de **lista** (hasta 10 filas) para elegir |
| `quick_replies` (hasta 3, ≤ 20 caracteres) | Botones bajo el último mensaje | **Botones de respuesta** (reply buttons) |
| `payment` | Botón "Pagar" | Botón de URL (CTA) o el link en el texto |

Las **plantillas aprobadas** sólo hacen falta para mensajes que inicia el negocio fuera de la
ventana de 24 h (recuperación de carritos, avisos de despacho días después). Las fotos de la
demo son ilustraciones propias servidas en `/static/products`; los canales reciben URL absoluta
(`PUBLIC_BASE_URL`), que en WhatsApp debe ser pública.

## 11. Etapa: cada negocio arma su agente (rama `feat/business-setup`)

Decisiones del usuario (26/10/2026): CRM propio del panel primero; catálogo y stock por CSV +
edición en el panel; "cómo habla" con plantilla por rubro + formulario.

Recorrido del dueño: registrarse → **Mi agente** (elige rubro, se precargan nombre del vendedor,
tono, saludo, preguntas frecuentes y reglas; ajusta y guarda; obtiene su **link de tienda**) →
**Catálogo** (sube CSV con productos, precios, stock y fotos; edita precio/stock/activo) →
comparte el link → los clientes conversan con su agente → **Oportunidades** y **Pedidos** en el
panel (avanza preparación/despacho/entrega).

- `agent_profiles` (uno por negocio): rubro, `public_slug` único, nombre del vendedor, tono,
  saludo, FAQ, reglas, envíos, horarios, medios de pago. El agente lo lee en cada turno; las FAQ
  y reglas son datos que el negocio afirma, y el control de respuestas los acepta como evidencia.
- Link público `/#/tienda/<slug>`: el servidor resuelve el negocio por el slug (identificador
  público, como la URL de una tienda); nunca por un tenant enviado por el cliente.
- Panel `/app/*` con RLS efectivo (`app_user`): perfil, catálogo, importación CSV, pedidos.
- CSV (encabezados en español): `sku, nombre, categoria, marca, precio, stock, descripcion,
  foto_url, color, ambiente, tipo, a_pedido, activo`. Validación por fila con errores
  devueltos; precio distinto ⇒ nuevo precio vigente desde hoy; stock ⇒ `on_hand` (nunca menor
  que lo apartado) con movimiento `adjust`.
- Fuera de esta etapa: Mercado Pago por negocio (OAuth), CRM externos, WhatsApp.
