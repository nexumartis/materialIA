# Funcionalidades de la competencia — qué conviene y cuándo

Relevamiento que pasó Tomi el 30/10/2026. Competidores: Brote, Comi, Zellen, WAEngine, MAMBO, Dialo, Scrapia, Ventasia y Colipia. La prioridad P0/P1/P2 es la del relevamiento.

Cada funcionalidad se evaluó con tres criterios:

1. **Si ya existe** en el producto.
2. **Si le sirve a nuestro cliente:** comercios de sanitarios, grifería y ferretería en Argentina, que hoy manejan el catálogo en Excel y venden por WhatsApp.
3. **Si respeta las reglas del producto** (`CLAUDE.md`): no inventar precios, stock ni medidas; un pago es pagado sólo si está verificado; deriva a una persona lo que no puede resolver.

Lo que se decidió está en el [roadmap](../roadmap.md#backlog-priorizado-competencia-30102026).

## Ya lo tenemos (no hace falta hacerlo)

| Funcionalidad | Dónde está |
|---|---|
| Probar el agente antes de publicarlo | Asistente paso a paso → Probar |
| Plantillas por industria | Asistente → Rubro |
| Políticas comerciales | Políticas que hace cumplir el servidor (zonas, mínimo, venta directa) |
| Memoria entre conversaciones y resumen de conversaciones largas | Memoria del cliente y compactación |
| Webchat | Tienda pública (`#/tienda/…`) |
| Historial de compras del cliente | Herramienta `historial_cliente` del agente |
| Seguimiento del pedido a pedido del cliente | «¿Cómo va mi pedido?» |
| Bandeja unificada (web) y detectar quién está sin responder | Conversaciones → filtro «Sin responder» |
| Etapas de venta y seguimientos con fecha | Oportunidades (etapas fijas, fecha de seguimiento y vencidos) |

## Conviene AHORA (no dependen de WhatsApp, mucho impacto para el rubro)

| Funcionalidad | Prioridad | Por qué |
|---|---|---|
| **Google Sheets como catálogo vivo** | P1 | El cliente ya vive en Excel. Que el catálogo se sincronice desde su planilla le ahorra el CSV. Es el mejor «onboarding» posible. |
| **Variantes y atributos** (color, terminación, medida) | P0 | En grifería un mismo modelo viene en cromo, negro o blanco. Hoy cada variante es un producto suelto y el agente las confunde. |
| **Productos sustitutos y búsqueda mejor** (semántica y por palabras) | P0 | Hoy hay normalización por palabras y alternativas cuando falta stock. Hay que mejorar el «no tengo ese, pero tengo este» sin inventar: sólo productos reales del catálogo. |
| **Cálculo de envío por zona o código postal** | P0 | Pregunta de todos los días. Hoy el agente sólo repite un texto. Se resuelve con una tabla de zonas y costos que carga el dueño, ya preparada en las políticas. |
| **Avisos al dueño** (derivación nueva, cliente sin atender hace X minutos) | P1 (push) / P0 (sin atender) | Hoy una derivación no le avisa a nadie: la bandeja existe, pero el dueño tiene que entrar a mirar. Se puede empezar con email o notificación web, sin WhatsApp. |
| **Roles de empleados, asignación de conversaciones y notas internas** | P0 / P1 / P1 | El comercio típico tiene más de una persona atendiendo. La bandeja ya respeta quién tiene la conversación; falta invitar empleados con permisos limitados. |
| **Alertas de stock bajo y movimientos de inventario** | P1 | La tabla de movimientos ya existe; falta mostrarla y avisar cuando algo está por agotarse. |
| **Seña o pago parcial para productos «a pedido»** | P1 | Inodoros, vanitorys y otros productos a pedido se trabajan con seña. Respeta las reglas: el pago parcial también tiene que estar verificado. |
| **Cancelar un pedido pendiente desde el chat** | P1 | Libera el stock apartado en el momento, en lugar de esperar que venza la reserva. |
| **Configuración desde la web o los PDFs del negocio** (tono, preguntas frecuentes, catálogo) | P0 / P1 | Acelera el asistente. **Condición:** lo que se lee de la web es una *propuesta* que el dueño revisa; un precio sacado de la web nunca se publica sin confirmar. Los PDFs en la base de conocimiento ya estaban pendientes. |
| **Fichas técnicas en PDF por producto** | P1 | Medidas e instalación son claves en sanitarios. El agente manda la ficha del fabricante en vez de describir medidas, que no puede inventar. |
| **Métricas de consumo y costo de IA** | P1 | Interno: saber cuánto cuesta cada negocio antes de fijar precios del servicio. |
| **Vista Kanban de oportunidades y etapas configurables** | P0 | Las etapas hoy son fijas. El Kanban es sobre todo front; las etapas configurables requieren migración. |
| **Exportar clientes (CSV)** | P1 | Simple. Cuidar la privacidad: sólo el dueño y sólo los datos que el negocio ya tiene. |

## Conviene CON WhatsApp (etapa 3)

Los mensajes **proactivos**, los que salen del negocio sin que el cliente escriba primero, necesitan WhatsApp con plantillas aprobadas. El chat web no puede «escribirle» a un cliente que cerró la pestaña.

| Funcionalidad | Prioridad |
|---|---|
| Recibir e interpretar audios del cliente | P0 |
| Recordatorio de pago pendiente | P0 |
| Recuperar carritos abandonados y clientes que no compraron | P0 |
| Avisos de pedido preparado, enviado y entregado, con tracking | P0 / P1 |
| Aviso cuando vuelve el stock | P1 |
| El dueño consulta ventas y actualiza precios o stock por WhatsApp (asistente del dueño) | P1 |
| Búsqueda por foto («se me rompió esta canilla») | P1 |
| Factura electrónica por WhatsApp | etapa 8 |
| Instagram Direct | P1 |
| Varios números de WhatsApp | P1 |

## Conviene DESPUÉS (campañas, etapa 5)

Campañas masivas y por segmentos, reactivación de leads e inactivos, promociones, cupones y reporte de ventas recuperadas.

Todas necesitan consentimiento y baja obligatorios, límite de frecuencia y que los descuentos los aplique el servidor, nunca el modelo.

## No por ahora (poco valor para el rubro o muy temprano)

- **Canales:** Messenger, Telegram, email como canal, atención por voz y respuestas con audio de IA.
- **Publicidad:** Meta Ads, TikTok Ads, ROAS y atribución a anuncios. Primero hay que tener ventas en WhatsApp para medir.
- **Integraciones fuera del mercado objetivo:** FUDO (gastronomía), Bsale (Chile), HubSpot, VTEX y WooCommerce. Shopify, sólo si aparece un cliente que lo use.
- **Productos:** catálogo con videos, audios explicativos de productos y programa de referidos.
- **Gestión:** clasificación por sentimiento, encuestas de satisfacción, métricas por vendedor y por sucursal.
- **Estructura:** múltiples sucursales con stock separado y multiempresa en una cuenta. Son un cambio grande del modelo de datos: hacerlos cuando un cliente real lo pida.
- **App móvil nativa:** primero una web instalable (PWA) con notificaciones.
- **API/MCP para agentes externos:** después de los eventos salientes (etapa 4).

**Para evaluar más adelante:**
- **Tango Tiendas** (P1, Dialo): tiene sentido en Argentina si los clientes lo usan. Entra junto con los conectores de la etapa 4.
- **Mercado Libre bidireccional y Tiendanube:** ya están previstos en la etapa 4.
