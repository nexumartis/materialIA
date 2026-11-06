# Brief para el directorio: materialIA

(Escrito para que alguien sin contexto lo entienda. Sin opinión sobre la idea.)

## La idea
Ver founder/idea.md. Resumen: SaaS argentino. Un agente de ventas por chat con IA para comercios PyME que vende de punta a punta con datos reales del negocio.

## Qué hace hoy el producto (construido, funcionando en local)
- Responde consultas con stock y precio reales del catálogo del comercio (CSV o Google Sheets sincronizada); nunca inventa precios ni stock; lo «a medida» o dudoso lo deriva a una persona.
- Arma el carrito, ofrece productos complementarios, pide envío o retiro: valida la dirección con la API pública Georef, calcula el costo por zona cargada por el negocio, ofrece día y franja con cupo (priorizando donde ya hay entregas cerca) o despacho por correo con número de seguimiento.
- Cobra: link de Mercado Pago (el pedido figura pagado sólo con la confirmación verificada del proveedor) o transferencia que el dueño coteja; señas para productos a pedido; constancia en PDF.
- Turnos (visitas, mediciones), reparto propio con hoja de ruta para el repartidor, bandeja para que una persona tome la conversación (con resumen), roles de equipo, campañas (carritos abandonados, cobranzas; envío hoy simulado), encuesta de satisfacción, webhooks salientes.
- Se instala en cualquier web con una línea de código (botón de chat configurable). Entiende fotos (busca el producto en el catálogo) y notas de voz.
- Panel del negocio con métricas de ventas, conversación y conversión.

## Cliente objetivo
Dueños de comercios PyME argentinos multi-rubro (ferretería/sanitarios, ropa, comida, electrodomésticos/colchones/muebles con entrega e instalación). Muchos sin tienda online. Hoy atienden por chat a mano.

## Competencia conocida (datos públicos)
- notchatbot: CRM omnicanal argentino con IA para ecommerce (WhatsApp, Instagram, TikTok, Mercado Libre, web). Muestra logos de +100 marcas (Nespresso, Arredo, Cheeky, Kevingston, Paula Cahen d'Anvers, Grisino…). «Planes desde USD 300/mes» según su ficha en la tienda de apps de Tiendanube; sin prueba gratis; instalación con llamada; integra Tiendanube, Shopify, VTEX, WooCommerce. Lleva al cliente al checkout de la tienda (no arma carrito ni cobra en el chat).
- Otros jugadores de chat/IA en LatAm existen (no relevados con detalle).

## Situación
- Dos socios fundadores técnicos. Producto en local, sin deploy, sin clientes pagos, sin precio definido.
- Sin WhatsApp todavía (requiere cuenta de Meta Business y cambio de alcance acordado).
- Presupuesto, tamaño de mercado, costo de adquisición: no informados (preguntas abiertas).
- Costo variable conocido: uso de IA por conversación (el equipo estimó de forma interna ~USD 4–30/mes por negocio chico y ~USD 85–600 por negocio grande; estimación, no medición).
