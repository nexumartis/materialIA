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

1. ~~**Comprobantes de pago**~~ **Hecho** (29/10/2026, PRs #16 y #17): transferencias con foto/PDF,
   OCR local, revisión del dueño, constancia en PDF y registro mensual. Migraciones 0008 y 0009
   (no aplicadas en la nube). Decisiones en
   [decisions/2026-10-29](decisions/2026-10-29-comprobantes-implementacion.md). Antes de un piloto
   real: almacenamiento privado de originales y retención.
2. **Bandeja y toma de control humana** (primer corte en la rama `feat/bandeja-humana`, 29/10/2026;
   [spec](superpowers/specs/2026-10-29-bandeja-humana-design.md); las sugerencias del agente quedan
   para un corte siguiente): ver todas las conversaciones, filtros (derivadas, con
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
6. **Crear el agente paso a paso** (mejor UX): asistente guiado con progreso:
   1. negocio · 2. rubro (plantilla) · 3. catálogo (CSV o conectar) · 4. cómo habla ·
   5. políticas · 6. cobro · 7. **probar** (chat de vista previa + pruebas) · 8. publicar (link,
   WhatsApp). "Mi agente" queda como pantalla de ajustes para después.
7. Envíos en el carrito, métricas, publicación en un servidor (staging) y producción.

## Orden sugerido

~~1~~ → **2** → 6 (en paralelo, es front) → 3 → 4 → 5 → 7. La bandeja humana va antes que WhatsApp porque
sin ella lo que el agente deriva queda sin atender; el asistente paso a paso puede avanzar en
paralelo porque no depende de los canales.
