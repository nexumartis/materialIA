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
   - **Eventos salientes**: tabla *outbox* en Postgres + worker que entrega webhooks firmados con
     reintentos. Con eso cualquier sistema (o Zapier/Make/n8n) se entera de pedidos, pagos y
     clientes sin integración a medida.
   - **Conectores entrantes** priorizados por demanda: stock/precios (Tiendanube, Mercado Libre,
     planilla), logística (tracking de Andreani/OCA/Correo u operador del negocio), cobros
     (Mercado Pago por negocio con su propia cuenta).
   - Una sola definición de pedido/cliente; cada conector traduce a ella.
5. **Campañas de marketing** (después de WhatsApp): segmentos a partir de la memoria y las
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

## Backlog priorizado (competencia, 30/10/2026)

Detalle y justificación en [research/2026-10-30-competencia](research/2026-10-30-competencia.md).

**Ahora (sin WhatsApp):**
1. Google Sheets como catálogo vivo.
2. Variantes y atributos de producto.
3. Envío por zona o código postal.
4. Sustitutos y búsqueda mejorada.
5. Avisos al dueño (derivaciones y clientes sin atender).
6. Roles de empleados, asignación y notas internas.
7. Alertas de stock bajo y movimientos de inventario.
8. Seña para productos a pedido.
9. Cancelar un pedido pendiente desde el chat.
10. Configuración desde la web o los PDFs del negocio, siempre como propuesta a revisar.
11. Fichas técnicas en PDF.
12. Costo de IA por negocio.
13. Kanban de oportunidades.

**Con WhatsApp (etapa 3):**
- audios del cliente;
- recordatorio de pago;
- carritos abandonados;
- avisos de envío y vuelta de stock;
- asistente del dueño por WhatsApp;
- búsqueda por foto;
- factura (etapa 8).

**Después:** campañas, cupones y reactivación (etapa 5).

**No por ahora:** canales secundarios (Messenger, Telegram, voz), publicidad paga, integraciones fuera del mercado objetivo, sucursales y multiempresa (hasta que un cliente lo pida) y app nativa.

## Orden sugerido

~~1~~ → ~~2~~ → ~~6~~ → 3 → 4 → 8 (facturación, requiere 3 y 4) → 5 → 7. La bandeja humana va antes que WhatsApp porque
sin ella lo que el agente deriva queda sin atender; el asistente paso a paso puede avanzar en
paralelo porque no depende de los canales.
