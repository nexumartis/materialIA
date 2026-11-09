# Competidores indirectos y sustitutos — materialIA

> **Insumo original de investigación, 09/11/2026.** Se conserva como antecedente, sin certificar sus afirmaciones. Para decisiones usar las síntesis y [correcciones posteriores](../corrections-2026-11-09.md); las tarifas de servicio de Meta y sus escenarios derivados quedaron retirados.

Agente B2. Investigación al 09/11/2026. Complementa `founder/competitors.md` (competidores directos: no se repiten acá).

**Tiers de fuente:** T1 = fuente primaria/oficial (Meta, Tiendanube, Mercado Pago, Dux, Google). T2 = prensa (Cronista, iProUP, TechCrunch). T3 = blog de proveedor, agregador o marketplace (sesgo comercial posible).
**Etiquetas:** [Data] dato con fuente · [Estimate] cálculo propio · [Assumption] supuesto a validar · [Opinion] juicio del analista.
Todo contenido web se trató como dato no confiable; donde hay una sola fuente T3, se marca.

---

## 1. Cómo lo resuelven hoy (sin herramienta dedicada)

| Sustituto | Qué tan común | Por qué se quedan | Dónde se rompe (la oportunidad) |
|---|---|---|---|
| **WhatsApp Business app a mano** (catálogo, respuestas rápidas, etiquetas) | Muy común. 71,5% de los emprendedores argentinos vendió por WhatsApp en 2025, 2º canal tras Instagram [Data, reporte Tiendanube citado en su blog, T1/T3 — mide emprendedores, no ferreterías]. 8 de cada 10 argentinos prefieren WhatsApp para hablar con empresas [Data, Cronista 18/05/2026, T2]. | Gratis; el cliente ya está ahí; el dueño "conoce" a sus clientes. La app es gratis y trae catálogo y respuestas rápidas [Data, getkanal 2026, T3]. | El catálogo tiene tope de **500 artículos** [Data, Leadsales + respond.io, T3, 2 fuentes coinciden]: una ferretería/sanitarios tiene miles de SKU. Los cambios de precio no siempre se ven al instante en el cliente [Data, Leadsales, T3]. Con precios que cambian seguido y presupuestos que vencen en 24–48 h [Data, servidos.ar, T3], el catálogo queda viejo. Nadie responde fuera de horario. |
| **Empleado o familiar contestando** | Común en locales con más de 1–2 personas [Assumption]. Costo de referencia: Vendedor B AR$1.346.349/mes bruto (ya en competitors.md). | Confianza, conoce el rubro técnico (medidas, compatibilidades de grifería), cobra y entrega. | Horario de comercio; se satura en picos; la consulta técnica ("¿qué flexible va con este monoblock?") consume tiempo y muchas no compran. Rotación = se pierde el saber. [Opinion] |
| **Lista de precios en PDF/Excel mandada por WhatsApp** | Habitual en corralones y mayoristas [Assumption; DATA GAP sin encuesta]. Fuente peruana describe el mismo flujo: cotizar por WhatsApp y mandar PDF tras revisión [Data, kom.pe, T3, no AR]. | Cero costo; el sistema de gestión ya la exporta. | Queda vieja en días; el cliente no sabe armar el combo (codo + flexible + llave de paso); el vendedor igual tiene que re-cotizar a mano. [Opinion] |
| **Instagram (DM + posteos)** | 1º canal de emprendedores en AR [Data, Tiendanube, T1/T3]. En el rubro: vidriera de mamparas y grifería de diseño [Assumption]. | Muestra producto; llega a público nuevo. | DMs se pierden; no hay stock ni precio vigente; deriva a WhatsApp igual. |
| **MercadoLibre como canal** | Común en grifería/sanitarios con marca [Assumption]. Comisión ~11,8–17,1% según categoría y tipo; "Hogar" 14–17% Clásica [Data, algoritmodigital/jaguarsheet ene-2026, T3, cifras discrepantes entre sí]. | Tráfico enorme, cobro y envío resueltos. | Comisión alta para productos pesados/voluminosos; no sirve para listas de obra con 20 ítems ni para asesorar; la relación es de ML, no del comercio. Muchos usan ML como vidriera y cierran por WhatsApp [Assumption]. |
| **Catálogo web gratis / "linktree"** (Tiendanube catálogo gratis, Changuito, etc.) | Existe y es gratis [Data, blog Tiendanube 2026, T1]. Changuito: tienda online con pedidos por WhatsApp, disponible en AR [Data, Capterra IL, T3]. Uso en el rubro: DATA GAP. | Fácil, link en la bio. | Hay que cargar y mantener miles de productos; no asesora; el pedido llega a WhatsApp y vuelve a ser manual. |

**Falla común que crea la oportunidad** [Opinion]: todos los sustitutos dependen de que *alguien mantenga una copia de precios y stock* (catálogo de WA, PDF, catálogo web) o de que *una persona conteste*. En un rubro con miles de SKU y precios móviles, esa copia siempre está vieja y la persona no está a las 22 h. materialIA lee la planilla que el local ya actualiza — no pide una copia nueva.

---

## 2. Productos adyacentes que podrían sumar la función

| Producto | Qué cubre hoy | Qué le falta vs. materialIA | Riesgo de que lo agregue |
|---|---|---|---|
| **Meta Business AI / Business Agent** (WhatsApp) | En AR desde feb-2026 (AR primero con otros 16 países LatAm) [Data, Cronista 18/05/2026, T2]. Se entrena con FAQs, chats, catálogo y web; recomienda productos; deriva a humano [Data, mismo]. Business Agent (Conversations, Londres 03/06/2026): "Closes sales", se conecta con "hundreds of systems like Shopify and Zendesk"; arranca gratis, luego suscripciones [Data, blog oficial WhatsApp, T1]. Cobro por tokens desde 01/08/2026, ~USD 2/M tokens [Data, wati/intelliconcierge, T3]. | Stock y precio vivos: usa el catálogo cargado (tope 500) [Data, Tiendanube ayuda 21/09/2026, T1 — es competidor, sesgado]. No hay pagos nativos en WhatsApp en AR. No arma listas de obra ni combos técnicos del rubro. | **Alto.** Ver sección 3. |
| **Mercado Pago** (link de pago, QR, Point) | Link de pago gratis de crear, sin web, cuotas, todos los medios [Data, mercadopago.com.ar, T1]. Asistente IA de MP lanzado ene-2026, pero para el *usuario consumidor* (100+ funciones de dinero) [Data, Forbes AR, T2]. | No tiene agente de ventas para el comercio; no lee stock; no conversa en WhatsApp por el comercio. | **Medio-bajo** como producto propio en 12 meses [Opinion]. MP es *infraestructura* de materialIA (dependencia, no competidor). |
| **Mercado Libre** | Agentes de IA de compra en prueba (MELI Experience, 10/09/2026, Rabinovich: "Las compras menos divertidas las va a hacer un robot por vos") [Data, iProUP, T2]. Agente vendedor por WhatsApp sólo para autos usados en México con Wonderful (ago-2026) [Data, descubre.vc, T2/T3]. "Seller Assistant" dentro de ML [Data, dev.to, T3, no verificado]. | Todo ocurre *dentro* del marketplace; nada para el canal propio del comercio. | **Bajo-medio** para el canal WhatsApp propio; **medio** para captar al comprador antes que llegue al local (agentes compradores). [Opinion] |
| **Tiendanube Chat Nube** (ex VICI) | Agente con stock, precios, variantes, envío y carrito en tiempo real; manda acceso directo al checkout [Data, ayuda Tiendanube 21/09/2026, T1]. +1,65M conversaciones, resuelve ~6 de 10 sin humano; sumó Instagram en 2026 [Data, prensa vía búsqueda, T2]. Compra completa en WhatsApp con alianza Meta (dic-2025) [Data, prensa, T2]. | **Requiere tienda Tiendanube**; no encontré oferta "sin tienda" [Data negativo, búsqueda 09/11/2026]. No lee Google Sheets ni sistemas de gestión del local. | **Medio.** Su camino natural es "abrí tu tienda gratis y prendé Chat Nube": convierte al comercio en cliente Tiendanube. Para un local con miles de SKU, cargar la tienda es la barrera. [Opinion] |
| **Sistemas de gestión** (Dux, Líder Gestión, Tango, Bejerman, Xubio, Colppy, Contabilium, nicho ferretero) | **Dux**: para pymes/ferreterías, desde ~USD 21 [Data, Capterra, T3]; genera links de MP desde la venta sin costo extra [Data, ayuda Dux, T1]; +4.500 negocios; integra Tiendanube y WhatsApp (sin detalle) [Data, app store Tiendanube, T1/T3]. **Líder Gestión**: licencia perpetua, integra WhatsApp, MP y Tiendanube (envío de facturas/avisos) [Data, GetApp, T3]. **Control Integral** (España): ERP ferretero con sync a tienda online [Data, interempresas, T2, no AR]. Tango/Bejerman/Xubio/Colppy/Contabilium: **DATA GAP** — no encontré funciones de agente conversacional. | Tienen el stock y precio "verdaderos", pero su "WhatsApp" es envío de comprobantes/avisos, no venta conversacional [Data parcial, T3]. | **Medio a 18–24 meses** [Estimate]: el que tiene el dato del stock puede enchufar el agente de Meta o un LLM. Hoy no hay señal concreta. También son **canal/aliado**: integrarse con Dux/Tango en vez de pelear. |
| **Google (Business Profile)** | El chat de Business Profile se cerró el 31/07/2024 [Data, 9to5Google/Android Central, T2]. "Let Google Call" (IA llama al local para preguntar stock y precio) y checkout agéntico: lanzados nov-2025 sólo en EE.UU., categorías acotadas [Data, TechCrunch 13/11/2025, T2]. | No hay canal de chat con el comercio en AR; nada en LatAm encontrado. | **Bajo** a 24 meses en AR [Estimate]. Señal a mirar: si Google trae "Let Google Call" a AR, el comprador consulta stock sin entrar a WhatsApp. |
| **Empretienda / Changuito / catálogos** | Tienda o catálogo con pedido por WhatsApp. | Sin IA, sin asesoramiento, sin stock vivo desde planilla. Precios: DATA GAP. | **Bajo-medio**: cualquiera puede sumar un bot genérico, pero no el know-how del rubro. |

---

## 3. Riesgo de plataforma

| Plataforma | Probabilidad de sumar stock real + pedido + cobro en el chat en AR | Plazo estimado | Señales concretas | Mitigación |
|---|---|---|---|---|
| **Meta (WhatsApp Business AI / Business Agent)** | **Alta** (65–75%) para "recomienda + cierra con link de pago de terceros"; **media** (35–45%) para stock en vivo desde fuente externa de una pyme sin ecommerce [Estimate] | 6–18 meses (mediados 2027) [Estimate] | Agente de IA ya en AR (feb-2026) [T2]; Business Agent "closes sales" e integra cientos de sistemas (03/06/2026) [T1]; "in-chat checkout" anunciado en Conversations 2026 [T3, sin confirmación oficial para AR]; Cliengo marca pagos WA en AR como "planificado" (tabla mar-2026) [T3]; WhatsApp Pay sigue en India/Brasil [T3]. | No competir en "responder preguntas" (eso Meta lo regala). Diferencial = **conector a la planilla/sistema del local + lógica de rubro** (combos, compatibilidades, listas de obra, unidades/medidas) + **verificación del pago MP** + instalación por los socios. Construir sobre la API oficial (coexistencia) para ser "el sistema que Meta llama", no su reemplazo. Cobrar por resultado/pedido, no por chat. |
| **Tiendanube (Chat Nube)** | **Media** (30–40%) de lanzar una versión "sin tienda" o "tienda importada desde planilla" [Estimate] | 12–24 meses [Estimate] | Compró VICI (fin 2024); Chat Nube ya hace stock+carrito+checkout dentro de su tienda [T1]; suma canales (Instagram 2026) [T2]; catálogo online gratis [T1]; ventas agénticas +10x vía ChatGPT [T3]. | Apuntar al comercio que **no quiere una tienda online** (miles de SKU, precios móviles, venta por obra). Ofrecer exportación fácil: si el comercio crece, no queda rehén. Diferenciarse en cotización de listas de obra (Chat Nube es carrito B2C). |
| **Mercado Libre / Mercado Pago** | **Baja-media** (15–25%) de un agente para el WhatsApp propio del comercio [Estimate] | 18–36 meses [Estimate] | Asistente MP orientado a consumidor (ene-2026) [T2]; agentes compradores en prueba (sep-2026) [T2]; agente vendedor por WhatsApp sólo autos MX (ago-2026) [T2/T3]. | MP es dependencia crítica: usar sólo API pública de links/webhooks, tener alternativa (transferencia/alias con verificación manual). Riesgo real es otro: que el comprador se vaya a ML con su agente; mitigar con velocidad de respuesta y precio de lista de obra. |
| **Google** | **Baja** (<15%) en AR [Estimate] | 24+ meses [Estimate] | Cerró chat de Business Profile (2024) [T2]; "Let Google Call" y checkout agéntico sólo EE.UU. (nov-2025) [T2]. | Monitorear. Si llega, materialIA puede ser quien responde la consulta con stock real (widget web indexable, datos de stock en el perfil). |
| **Sistemas de gestión (Dux, Tango, etc.)** | **Media** (25–35%) de que alguno sume un "vendedor IA" propio [Estimate] | 18–24 meses [Estimate] | Dux ya genera links MP e integra WhatsApp/Tiendanube [T1/T3]; ninguna señal de agente conversacional encontrada. | Convertirlos en **canal**: conector oficial a Dux/Tango además de Google Sheets; programa de referidos para sus partners/implementadores. |

**Plataforma de mayor riesgo:** Meta. Ya está en Argentina, es gratis/centavos, y sólo le faltan dos piezas para pisar el núcleo de materialIA: stock vivo desde una fuente externa y cobro dentro del chat. [Opinion]

---

## 4. Alternativas gratis, open source y freelancers

| Alternativa | Costo | Qué logra | Dónde se queda corta |
|---|---|---|---|
| **n8n + plantillas** | Self-host gratis; nube con plan pago (precio no verificado: DATA GAP) | Existen tutoriales de bot de pedidos por WhatsApp que consulta inventario en Google Sheets, sugiere alternativas y guarda pedidos en otra hoja [Data, growwstacks, T3]; otro con cobro vía Stripe [Data, growwstacks, T3]. No encontré plantilla con **Mercado Pago** [Data negativo]. | Requiere alguien técnico; mantenimiento; sin lógica de rubro; Mercado Pago a mano por HTTP/webhook. |
| **Typebot** | Self-host gratis y open source [Data, techreviewer/fitgap, T3]; nube con planes (precio: DATA GAP) | Flujos guiados (menús). | No es agente: no entiende "necesito todo para un baño". |
| **Chatwoot** | Community self-host gratis (MIT), necesita servidor 4 GB RAM/2 CPU; nube ~USD 19–99/agente/mes; plan gratis de 2 agentes según una fuente [Data, eesel/achiya, T3, cifras dispares] | Bandeja unificada WA + web + humanos. Captain AI sólo en planes pagos [T3]. | Es bandeja, no vendedor; no lee stock ni cobra. |
| **Bot casero con ChatGPT / Gemini** | Tokens + API de WhatsApp | Respuestas "inteligentes". | Alucina precios si no está conectado a la planilla; sin verificación de pago. [Opinion] |
| **Freelancer Workana** | Proyecto de agente IA WhatsApp: **USD 300–500**, 2–3 semanas, pago por hitos [Data, workana.com, T3, 1 proyecto]; otros sin monto [T3]. Hay un pedido publicado de "agente WhatsApp para tienda de bebidas con stock y procesamiento de pedidos" (403 al abrir; existe por título) [Data parcial, T3]. | Bot a medida, pago único. | Sin soporte posterior; se rompe cuando cambia la planilla o la API de Meta; el comercio queda solo. |
| **Freelancer Fiverr** | Gigs desde **USD 30** básico y "hasta USD 50" [Data, fiverr.com, T3]; varios excluyen costos de API de Meta [T3]. | n8n + Sheets + IA "inventory, orders, FAQs". | Calidad muy variable, en inglés, sin conocimiento del rubro ni de MP argentino. |
| **Plataformas no-code AR** | Desde gratis a ~USD 50/mes [Data, duotach, T3]; total pyme 1.000 conversaciones ~AR$60.000–150.000/mes con IA [Data, yo-facturo, T3]. | — | Genéricas. |

**Lectura** [Opinion]: el sustituto "hágalo usted mismo" cuesta USD 30–500 de una vez + tokens. materialIA (USD 44/mes) gana si vende **resultado mantenido** (anda cuando cambia la planilla, cuando Meta cambia reglas, verifica el pago) e instalación incluida. Recuperar el pago único del freelancer le lleva al comercio 1–11 meses de materialIA [Estimate: 30–500 / 44], por lo que el precio no es la barrera; la confianza sí.

---

## 5. Costos de cambio

**Qué ata al comercio a lo que usa hoy**
- **El número de WhatsApp y el historial de chats.** Es el activo más sensible [Opinion]. Mitigado por la **Coexistencia** (Business App + Cloud API en el mismo número), oficial de Meta desde 06/05/2025, con soporte en Argentina según tabla de un proveedor; se conservaría historial (hasta 6 meses, no confirmado) y es reversible [Data, Chakra/Cliengo/proveedores, T3 — verificar en docs de Meta]. Límite: un número con coexistencia por cuenta [T3].
- **Hábito y costo cero** del manejo manual; el dueño "sabe" contestar. [Opinion]
- **El empleado**: despedir o reasignar tiene costo emocional y laboral; materialIA debe venderse como "le saca lo repetitivo al vendedor", no como reemplazo. [Opinion]
- **Sistema de gestión ya pago** (Dux, Tango): si el stock vive ahí y no en Sheets, la planilla es un paso extra. [Assumption]
- **Clientes acostumbrados** a la lista PDF o a pedir "lo de siempre". [Assumption]
- **Desconfianza en la IA**: miedo a que cotice mal (en el rubro una medida equivocada es una devolución). [Opinion]

**Qué lo haría cambiar**
- Pérdida visible de ventas fuera de horario o en picos (temporada de obra). [Assumption]
- Que el agente **no exija cargar nada nuevo** (usa la planilla que ya actualiza). [Opinion]
- Prueba concreta: pedidos cobrados y verificados en las primeras 2 semanas. [Opinion]
- Instalación hecha por los socios (barrera técnica cero) y precio en pesos (casi todos los SaaS cobran en USD; ver competitors.md). [Data/Opinion]
- Un caso conocido del barrio/rubro que ya lo use. [Assumption]

---

## Data gaps

1. **Uso real por canal en ferreterías/sanitarios de CABA** (WhatsApp manual vs. empleado vs. PDF vs. ML vs. Instagram): no hay encuesta pública del rubro. Sólo dato de emprendedores en general (Tiendanube). → Validar en entrevistas.
2. **Pagos dentro de WhatsApp en Argentina**: sin anuncio oficial de Meta; sólo tabla de un proveedor ("planificado").
3. **Stock en vivo desde fuentes externas en Meta Business Agent**: la página oficial no lo menciona; tampoco precio de suscripción futuro.
4. **Tango, Bejerman, Xubio, Colppy, Contabilium**: no se encontraron funciones de agente conversacional ni roadmap; no verificado.
5. **Precios de nube de n8n y Typebot**, y de Empretienda/Changuito/Pedix.
6. **Comisiones exactas de MercadoLibre para grifería/sanitarios** (fuentes T3 discrepan).
7. **Detalle de la nota iProUP sobre Tiendanube "la IA arma el carrito y cobra"**: sólo se pudo leer el titular.
8. **Workana**: el proyecto de "tienda de bebidas con stock y pedidos" devolvió 403; presupuesto desconocido.
9. **Coexistencia en Argentina**: confirmada sólo por proveedores, no por documentación de Meta leída.

---

## Fuentes con links

T1 (oficial)
- WhatsApp Business blog — Conversations 2026, Meta Business Agent (03/06/2026): https://whatsappbusiness.com/blog/introducing-meta-business-agent-ai/
- Ayuda Tiendanube — Chat Nube vs IA de WhatsApp Business (act. 21/09/2026): https://ayuda.tiendanube.com/responde-con-chat-nube/por-que-elegir-chat-nube-frente-a-la-ia-de-whatsapp-business
- Tiendanube blog — Cómo vender por WhatsApp 2026: https://www.tiendanube.com/blog/como-vender-por-whatsapp/
- Mercado Pago — Link de pago: https://www.mercadopago.com.ar/herramientas-para-vender/link-de-pago
- Ayuda Dux — Pasarelas de pago: https://intercom.help/duxsoftware/es/articles/8822877-pasarelas-de-pago
- Tiendanube app store — Dux Software ERP: https://www.tiendanube.com/tienda-aplicaciones-nube/dux-software-erp

T2 (prensa)
- El Cronista — novedad de WhatsApp para pymes (18/05/2026): https://www.cronista.com/infotechnology/it-business/asi-funciona-la-novedad-de-whatsapp-que-usan-las-pymes-para-vender-mas-sin-sumar-personal/
- Forbes Argentina — asistentes financieros (MP, ene-2026): https://www.forbesargentina.com/innovacion/arranca-era-asistentes-virtuales-financieros-son-como-utilizarlos-n84446
- iProUP — Mercado Libre prueba agentes de IA (10/09/2026): https://www.iproup.com/innovacion/71442-mercado-libre-ya-prueba-agentes-de-ia-y-robots-para-entregas.amp
- iProUP — Tiendanube ventas automáticas en WhatsApp (sólo titular): https://www.iproup.com/innovacion/62792-tiendanube-integra-ventas-automaticas-en-whatsapp-la-ia-ahora-arma-el-carrito-y-cobra
- LatamList — Tiendanube adquiere VICI: https://latamlist.com/?p=17297
- Mercado.com.ar — Tiendanube suma Instagram a Chat Nube: https://mercado.com.ar/ruta-digital/tiendanube-suma-instagram-a-chat-nube-y-amplia-su-estrategia-de-comercio-conversacional
- descubre.vc — Mercado Libre y Wonderful, agentes para autos MX (ago-2026): https://www.descubre.vc/noticia/wonderful-y-mercado-libre-implementan-agentes-de-ia-para-la-venta-de-autos-en-m-xico-2026-08-20
- TechCrunch — Google agentic checkout y "Let Google Call" (13/11/2025): https://techcrunch.com/2025/11/13/google-expands-ai-shopping-with-conversational-search-agentic-checkout-and-an-ai-that-calls-stores-for-you
- 9to5Google — cierre de Business Messages (28/05/2024): https://9to5google.com/2024/05/28/google-business-messages-shutting-down/
- Interempresas — Control Integral, software ferretero: https://www.interempresas.net/Ferreteria/185576-Entrevista-a-Isidre-Argerich-director-comercial-de-Control-Integral.html

T3 (proveedores, agregadores, marketplaces)
- Cliengo — Guía WhatsApp Payments 2026: https://guiawabusiness.cliengo.com/whatsapp-payments
- Cliengo — Coexistence 2026: https://guiawabusiness.cliengo.com/coexistence
- Chakra — Coexistence support por país: https://chakrahq.com/product/whatsapp/tools/whatsapp-coexistence-support
- Wati — Meta WhatsApp AI token pricing: https://www.wati.io/en/blog/meta-whatsapp-ai-token-pricing/
- Intelliconcierge — Meta Business Agent pricing: https://www.intelliconcierge.com/blog/meta-business-agent-pricing-what-whatsapp-businesses-need-to-know-in-2026
- Leadsales — problemas del catálogo de WhatsApp: https://leadsales.io/blog/problemas-catalogo-de-whatsapp/
- respond.io — catálogo de WhatsApp: https://respond.io/es/blog/whatsapp-catalog-whatsapp-shopping-catalog
- getkanal — precios WhatsApp Business 2026: https://getkanal.com/es/blog/precios-whatsapp-business
- servidos.ar — dónde comprar materiales (vigencia de presupuestos): https://servidos.ar/donde-comprar
- kom.pe — catálogo virtual ferreterías (Perú): https://kom.pe/catalogo-virtual-ferreterias-peru/
- Capterra — Dux Software: https://www.capterra.es/software/213765/dux-software
- GetApp — Líder Gestión: https://www.getapp.co.uk/software/2080119/lider-gestion
- Capterra IL — Changuito: https://www.capterra.co.il/software/1107103/Changuito
- algoritmodigital — comisiones Mercado Libre: https://algoritmodigital.com.ar/cuanto-es-la-comision-de-mercado-libre-por-vender/
- jaguarsheet — comisiones ML 2026: https://jaguarsheet.com/es/blog/comisiones-mercado-libre
- growwstacks — bot de pedidos WhatsApp con n8n + Sheets: https://growwstacks.com/blog/whatsapp-order-bot-n8n-automation
- growwstacks — agente que cobra con n8n: https://growwstacks.com/blog/whatsapp-ai-agent-takes-payments-n8n-tutorial/
- Workana — agente IA WhatsApp (USD 300–500): https://www.workana.com/es/job/implementacion-de-agente-ia
- Workana — agente WhatsApp tienda de bebidas con stock (403): https://www.workana.com/en/job/whatsapp-ai-agent-mvp-development-for-beverage-store-with-stock-management-and-order-processing
- Fiverr — gig WhatsApp + n8n + Sheets: https://fiverr.com/jaimeasp/automate-whatsapp-with-n8n-openai-and-google-sheets
- Fiverr — gig chatbot ventas/pedidos: https://fiverr.com/salmansaleem_/whatsapp-ai-chatbot-for-sales-support-orders-lead-gen
- eesel — Chatwoot pricing 2026: https://www.eesel.ai/blog/chatwoot-pricing
- achiya-automation — Chatwoot self-host vs cloud: https://achiya-automation.com/en/blog/chatwoot-pricing/
- techreviewer — Typebot: https://techreviewer.co/products/typebot
- yo-facturo — bot WhatsApp Argentina IA (costos en pesos): https://yo-facturo.com/blog/bot-whatsapp-argentina-ia/
- duotach — mejores chatbots WhatsApp Argentina: https://duotach.com/blog/mejores-chatbots-whatsapp-argentina
- Botias — agentes IA Argentina con link MP: https://botias.io/agentes-ia-argentina
- dev.to — Seller Assistant de ML (opinión): https://dev.to/yanmoheluo/amazon-has-third-gen-agents-mercado-libre-sellers-still-reply-by-hand-in-spanish-1cm7
