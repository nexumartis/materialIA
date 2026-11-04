# Hoja de ruta del producto

Visión acordada con Tomi el 27/10/2026. El estado técnico vigente está en
[current-state.md](current-state.md). Cada etapa se especifica y revisa antes de implementarse.

## Principio: un solo cerebro

El negocio ya tiene (o va a tener) varios sistemas: logística, cobros, facturación, CRM. El agente
**no** debe convertirse en un sistema más que hay que sincronizar a mano. La plataforma es el
centro: el pedido, el cliente y la conversación viven acá, y los demás sistemas se enteran por
**eventos** o se consultan por **conectores**. Nada de lógica de negocio duplicada en cada
integración.

```
            ┌──────────── canales ────────────┐
            │  WhatsApp · Instagram · web     │
            └───────────────┬─────────────────┘
                            ▼
   panel ◄──────►  AGENTE + PEDIDOS + CLIENTES  ──► eventos (pedido.creado, pedido.pagado,
   (humano toma       (fuente de verdad)            pedido.despachado, cliente.nuevo…)
    el control)             ▲                              │
                            │ conectores                   ▼
              stock · precios · tracking          webhooks / Zapier · Make · n8n /
              (Tiendanube, ML, ERP…)              logística · facturación · CRM externos
```

## Etapas

1. ~~**Comprobantes de pago**~~ **Hecho** (29/10/2026, PRs #16, #17 y #18): transferencias con foto/PDF,
   OCR local, revisión del dueño, constancia en PDF y registro mensual. Migraciones 0008 y 0009
   (aplicadas en la nube el 29/10). Decisiones en
   [decisions/2026-10-29](decisions/2026-10-29-comprobantes-implementacion.md). Antes de un piloto
   real: almacenamiento privado de originales y retención.
2. ~~**Bandeja y toma de control humana**~~ **Hecho** (29/10/2026, PR #19, migración 0010;
   [spec](superpowers/specs/2026-10-29-bandeja-humana-design.md)). **Pendiente:** que el agente
   sugiera respuestas al humano. ver todas las conversaciones, filtros (derivadas, con
   pedido, sin responder), **tomar el control** (el agente se pausa en esa conversación),
   responder, devolverla al agente. El agente sugiere respuestas al humano. Base para WhatsApp.
3. **WhatsApp e Instagram** (requiere cambiar el alcance en CLAUDE.md con ambos socios y cuenta de
   Meta Business): adaptador de canal sobre la misma conversación; identidad del cliente por
   teléfono (ya preparada en `customer_identities`); ventana de 24 h y plantillas aprobadas;
   mensajes interactivos (listas, botones) ya modelados en `messages.payload`.
4. **Integraciones sin "muchos cerebros"**:
   - ~~**Eventos salientes**~~ **Hecho** (PR #47, migración 0021): webhooks firmados con outbox y reintentos.
     Antes: tabla *outbox* en Postgres + worker que entrega webhooks firmados con
     reintentos. Con eso cualquier sistema (o Zapier/Make/n8n) se entera de pedidos, pagos y
     clientes sin integración a medida.
   - **Conectores entrantes** priorizados por demanda: stock/precios (Tiendanube, Mercado Libre,
     planilla), logística (tracking de Andreani/OCA/Correo u operador del negocio), cobros
     (Mercado Pago por negocio con su propia cuenta).
   - Una sola definición de pedido/cliente; cada conector traduce a ella.
5. **Campañas de marketing** — **Base hecha** (04/11/2026, PR #64, migración 0028): audiencias
   (carrito abandonado, pagos pendientes, compraron, consultaron y no compraron, inactivos), mensaje
   con datos reales, baja pedida en la charla, tope de frecuencia y atribución. **El envío es
   simulado** hasta que se habiliten los envíos a clientes (WhatsApp). Diseño original: segmentos a partir de la memoria y las
   compras (p. ej. "compró grifería hace 6 meses", "consultó y no compró"), plantillas aprobadas,
   programación por el worker, **consentimiento y bajas** obligatorios, límite de frecuencia y
   atribución de ventas a la campaña.
6. ~~**Crear el agente paso a paso**~~ **Hecho** (29/10/2026, PRs #21 y #22;
   [spec](superpowers/specs/2026-10-29-asistente-agente-design.md)). Faltan WhatsApp y los
   conectores de catálogo. Asistente guiado con progreso:
   1. negocio · 2. rubro (plantilla) · 3. catálogo (CSV o conectar) · 4. cómo habla ·
   5. políticas · 6. cobro · 7. **probar** (chat de vista previa + pruebas) · 8. publicar (link,
   WhatsApp). "Mi agente" queda como pantalla de ajustes para después.
7. Envíos en el carrito, métricas, publicación en un servidor (staging) y producción.
8. **Facturación electrónica con ARCA** (pedida por Tomi el 30/10/2026). **Cambia el alcance:** hoy
   la constancia de compra dice «no es factura fiscal» y la facturación quedó fuera
   ([decisión del 26/10](decisions/2026-10-26-comprobantes-clientes.md)). Requiere acuerdo de ambos
   socios y validación de un contador. Flujo pedido:
   1. El cliente compra por WhatsApp (depende de la etapa 3).
   2. Mercado Pago confirma el pago (verificado con el proveedor, como hoy; requiere MP por negocio,
      etapa 4).
   3. El backend genera una **solicitud de facturación** por pedido pagado, única e idempotente:
      nunca dos facturas para el mismo pedido.
   4. Se emite la **factura electrónica** con ARCA (web service de factura electrónica, WSFE) y se
      obtiene el **CAE**.
   5. Se guardan el **CAE**, el **número de comprobante** (punto de venta y número) y el
      **vencimiento del CAE**, junto con el tipo de comprobante y los importes enviados.
   6. Se envía la **factura en PDF** al cliente por WhatsApp. La entrega se registra recién cuando
      ocurre.

   **Qué hay que construir:**
   - **Datos fiscales por negocio:** CUIT, condición frente al IVA, punto de venta habilitado para
     web services y **certificado digital** con su clave privada. Van en el mecanismo de secretos,
     nunca en Git ni en la base en claro. Hay que decidir si cada negocio usa su propio
     certificado o si delega el servicio en la plataforma.
   - **Datos del cliente para facturar:** tipo y número de documento (DNI o CUIT) y condición
     frente al IVA. Hoy el chat no los pide: el agente los tiene que solicitar antes de pagar, o
     se factura a consumidor final dentro de los límites que permita la normativa (a verificar).
   - **Tipo de comprobante** (A, B o C) según la condición del emisor y del receptor; los importes
     y el IVA salen del pedido, nunca del modelo.
   - **Cola de facturación en el worker:** reintentos si ARCA no responde, consulta del último
     comprobante autorizado antes de reintentar (para no duplicar ni saltear números) y estado
     visible en Pedidos: «pendiente / emitida / rechazada (motivo)».
   - **PDF de la factura** con los datos que exige la normativa, incluido el **código QR** (a
     verificar con las especificaciones vigentes de ARCA).
   - **Nota de crédito** cuando se devuelve un pago ya facturado (hoy el pedido pasa a
     «reintegrado» y la constancia queda ANULADA).
   - **Homologación primero:** probar en el entorno de prueba de ARCA con datos sintéticos antes
     de emitir en producción.

   **Honestidad:** un pedido figura «facturado» sólo con el CAE devuelto por ARCA. Si ARCA rechaza o
   no responde, se dice y queda para revisión; nunca se genera un PDF de factura sin CAE.
   **Dependencias:** WhatsApp (etapa 3) para la entrega, Mercado Pago por negocio (etapa 4) y la
   validación contable. Mientras no exista WhatsApp, la factura puede entregarse por el chat web
   o descargarse desde el panel, como la constancia actual.

## Backlog priorizado (actualizado 04/11/2026)

Fuentes: [research/2026-10-30-competencia](research/2026-10-30-competencia.md) y el análisis de
**notchatbot** del 04/11/2026 (CRM omnicanal argentino con IA para ecommerce: +100 marcas como
Nespresso, Arredo, Cheeky o Kevingston; WhatsApp/IG/TikTok/ML/web; entiende fotos y audios;
integra Tiendanube, Shopify, VTEX y WooCommerce; «Planes desde USD 300/mes» según su ficha en la
tienda de apps de Tiendanube; instalación con llamada, sin prueba gratis).
**Nuestra diferencia:** ellos mandan al checkout de la tienda; nosotros cerramos en el chat (carrito,
envío/retiro, cobro verificado, seña, turnos) y funcionamos sin tienda online.

**Hecho del backlog del 30/10:** Google Sheets (#29), variantes (#33), envío por zona + Georef
(#31, #40), búsqueda y sustitutos (#34), movimientos de stock (#35), configuración desde la web
(#36), roles (#37), seña (#39), costo de IA (#32), límites de IA (#41), avisos al dueño (#57),
cancelar desde el chat. Además: webhooks (#47), encuesta de satisfacción (#46), resumen al derivar
(#48), métricas de bandeja (#49), privacidad (#50), turnos (#54), recompra (#53), entrega antes de
confirmar (#60), seguridad y RLS rápido (#61), campañas (#64) y chat instalable en cualquier web
con una línea (#65).

**Ahora (sin WhatsApp), en este orden:**
1. **Fotos del cliente → producto del catálogo** en el chat web (sale del grupo «con WhatsApp»):
   precio y stock siempre del catálogo; si la coincidencia es dudosa, deriva (`requires_human`).
2. **Audios del cliente** en el chat web: transcripción y respuesta como texto; sin IA, se dice
   explícitamente (`mode:"mock"`), nunca se finge.
3. **Conector de catálogo Tiendanube** (stock y precio, sólo lectura) + app en su tienda de apps que
   inyecta el script del chat. Después WooCommerce y Shopify.
4. **Onboarding sin llamada:** «pegá tu web» propone FAQ, horario y políticas para aprobar (nunca
   precios); prueba gratis y precio público por debajo de la competencia.
5. **Encuesta NPS + tickets con plazo (SLA)** sobre la bandeja actual.
6. Fichas técnicas en PDF y Kanban de oportunidades (pendientes del 30/10).
7. Escalabilidad (auditoría 04/11): topes de IA por negocio, worker con tiempo por tarea, IA fuera de
   las transacciones, Mercado Pago por negocio, retención y observabilidad.

**Entregas y logística: dónde termina lo nuestro (04/11/2026).** Somos el que vende; no operamos la
logística del negocio.
- **Sí (hecho, PRs #68 y siguiente):** el agente ofrece día y franja con cupo, primero donde ya hay una
  entrega cerca (< 2 km); la entrega se agenda sola al pagarse; Agenda única (turnos + entregas);
  hoja de ruta simple para quien reparte (salí / llegué / entregado, avisos al cliente); envío por
  correo con número de seguimiento cargado a mano y avisado en el chat; zonas «por correo» y
  «Todo el país»; **módulos** por negocio (turnos, reparto propio, correo, retiro, señas, campañas).
- **Quién va lo decide una persona del negocio** (o el único repartidor, si hay uno). El agente nunca asigna.
- **No vamos a hacer:** ruteo óptimo y gestión de flota, GPS en vivo, etiquetas y cotización
  automática de correos con API propia por correo. Cada correo (Andreani, OCA, Correo Argentino) pide
  contrato y credenciales por negocio: si un cliente lo necesita, integrar **un agregador** de envíos
  (a evaluar: precio, cobertura, API pública) o recibir el estado por webhook/CSV. Para logística
  avanzada, el negocio usa su herramienta y se conecta por **webhooks** (`order.paid`, `order.shipped`).

**Con WhatsApp (etapa 3):** recordatorio de pago y carritos abandonados reales (las campañas ya
existen, cambia el canal), avisos de envío y vuelta de stock, asistente del dueño por WhatsApp,
Instagram, factura (etapa 8).

**Después:** cupones, MCP para consultar el negocio desde Claude/ChatGPT.

**No por ahora:** canales secundarios (Messenger, Telegram, voz), publicidad paga, integraciones fuera del mercado objetivo, sucursales y multiempresa (hasta que un cliente lo pida) y app nativa.

## Orden sugerido

~~1~~ → ~~2~~ → ~~6~~ → 3 → 4 → 8 (facturación, requiere 3 y 4) → 5 → 7. La bandeja humana va antes que WhatsApp porque
sin ella lo que el agente deriva queda sin atender; el asistente paso a paso puede avanzar en
paralelo porque no depende de los canales.
