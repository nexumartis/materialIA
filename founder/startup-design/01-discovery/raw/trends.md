# Tendencias y momento: materialIA (A2, Industry Trends & Timing)

> **Insumo original de investigación, 09/11/2026.** Se conserva como antecedente, sin certificar sus afirmaciones. Para decisiones usar las síntesis y [correcciones posteriores](../corrections-2026-11-09.md); las tarifas de servicio de Meta y sus escenarios derivados quedaron retirados.

Fecha de corte: 09/11/2026. Complementa `founder/competitors.md` (no repite su tabla ni su análisis de quejas).

**Leyenda.** Tier 1: fuente oficial o consultora (Meta for Developers, INDEC, BCRA, Gartner). Tier 2: prensa seria o comunicado. Tier 3: blog, proveedor o agregador. Etiquetas: [Data] dato publicado, [Estimate] cuenta propia o cruce de fuentes, [Assumption] supuesto, [Opinion] juicio. **VIEJO** = más de 18 meses (anterior a mayo de 2025).

---

## 1. Tendencias tecnológicas

### T1. El agente de IA de Meta ya viene adentro de WhatsApp Business
- **Qué pasó.** [Data] Business AI llegó a Argentina en **febrero de 2026**, junto con otros 16 países de LatAm. Se entrena con preguntas frecuentes, chats anteriores, el catálogo y la web del comercio. Recomienda productos y deriva a una persona sin perder el contexto (Cronista, 18/05/2026, tier 2, con citas de Meta Argentina). El **03/06/2026** Meta lo lanzó a nivel global como "Meta Business Agent": responde, recomienda, agenda turnos, califica leads y deriva a humanos. Se probó casi 2 años en India y México (TechCrunch, 03/06/2026, tier 2). Cliengo habla de más de 1 millón de negocios en la beta (09/10/2026, tier 3).
- **Precio.** [Data] Por la API se cobra **USD 2 por millón de tokens**, entre 20.000 y 25.000 tokens por mensaje: **unos USD 0,04–0,05 por mensaje**, sin tramo gratis y sin descuento por volumen. Es categoría de mensaje propia desde el 01/07/2026, y en la API se cobra desde el 01/08/2026 (Meta for Developers, tier 1). En la app, el acceso base es gratis y la cuota sube con **Meta One** (lanzado el 15/09/2026): Essential desde USD 14,99/mes, Advanced 49,99, Expert 149 y Max 499 (Culturageek AR, 16/09/2026, tier 2). Meta no publica cuántas respuestas trae cada plan.
- **Lo que no hace (todavía).** [Data] Ninguna fuente de Meta menciona stock, carrito, pedido ni cobro para el agente de la app (TechCrunch y la guía de Cliengo). Lo anunciado es una plataforma para empresas grandes que conecta agentes con sistemas como Shopify, Zendesk o Shopee, y "Business Discovery" (buscar un negocio por nombre), marcado como "próximamente".
- **Etapa:** adopción temprana a masiva en pymes (viene gratis y preinstalado). **Amenaza alta** para "responder preguntas"; **amenaza baja hoy** para "stock real + pedido + cobro verificado". **Plazo** del riesgo: 12–24 meses [Opinion], si Meta abre conectores de inventario a pymes o habilita pagos en AR.

### T2. Tiendanube cierra la venta dentro de WhatsApp, pero sólo para sus tiendas
- [Data] En **InnovA 2026**, anunciado el 08/12/2025, Tiendanube y Meta lanzaron en Argentina la compra completa por WhatsApp: la IA elige productos, arma el carrito y cobra con **Pago Nube**. Según la empresa, 7 de cada 10 consultas se resuelven sin intervención humana (Mercado, tier 2; iProUP, tier 2). El agente interpreta texto, imágenes y **audios** (iProUP, tier 2). En 2026 sumó Instagram (Mercado, tier 2). El origen es la compra de **VICI**, una startup argentina de agente para WhatsApp, en **junio de 2025** (LatamList / Descubre.vc, tier 2; PitchBook, 10/06/2025, tier 1). En la beta de 3 meses pasó el millón de conversaciones.
- **Etapa:** crecimiento dentro de la base de Tiendanube (unos 160.000 comercios en LatAm). **Amenaza media**: valida el formato "agente que cobra en el chat" y le enseña al mercado qué esperar, pero exige tienda Tiendanube. **Plazo:** si abren Chat Nube a comercios sin tienda, 6–18 meses [Opinion].

### T3. Pagos dentro de WhatsApp: no hay en Argentina
- [Data] Hay checkout y pagos dentro del chat en **Brasil** (Pix, tarjeta) y en **México** (Global Payments API desde el 12/05/2026). El resto de LatAm usa links o Flows con pasarelas locales como Mercado Pago (Cliengo, 09/10/2026, tier 3). Un agregador lista a Argentina como "planificado", sin pasarela confirmada (Cliengo/whatsapp-payments, tier 3). **No encontré ningún anuncio oficial de Meta ni de Mercado Pago para Argentina en 2026.**
- [Data] Mercado Pago lanzó en Argentina un asistente de IA para **usuarios** (pagar, transferir e invertir por texto o voz), no para vendedores (DPL News / iProUP, tier 2). Según iProUP (agosto de 2026, tier 2), Mercado Libre y Mercado Pago son el caso más avanzado de pagos agénticos en el país.
- **Etapa:** no disponible en AR. **Oportunidad:** hoy el link de pago de Mercado Pago es la forma normal de cobrar por WhatsApp en Argentina, y materialIA ya lo usa. **Amenaza** cuando Meta habilite pagos nativos en AR. Plazo desconocido (ver Data gaps).

### T4. "Comercio agéntico" y compras desde asistentes externos
- [Data] Tiendanube se sumó al directorio de Claude (julio de 2026) y reporta que las ventas vía ChatGPT se multiplicaron por 10 en Argentina (Ecosistema Startup, tier 3). Mercado Libre, Tiendanube y las tarjetas están probando pagos agénticos (iProUP, agosto de 2026, tier 2).
- **Etapa:** experimental. **Para materialIA: neutro en el corto plazo** [Opinion]. El comprador de sanitarios en CABA sigue escribiendo por WhatsApp, no le pide a ChatGPT que compre un inodoro. A 2028, Gartner prevé que muchos recorridos de atención empiecen en asistentes de terceros (ver Predicciones).

### T5. Startups de IA en WhatsApp con foco transaccional
- Ver la sección Inversión. La señal es que el dinero va a agentes que **mueven plata o cierran pedidos** (Jelou, Vambe), no a bots que sólo responden.

---

## 2. Precios de la API de WhatsApp para Argentina (noviembre de 2026)

**Modelo vigente** [Data, Meta for Developers, tier 1]:
- Desde el **01/07/2025** se cobra **por mensaje entregado**, según categoría y país. Antes se cobraba por conversación de 24 h. Los mensajes que manda el cliente no se cobran.
- **Cambio clave del 01/10/2026:** vuelven a cobrarse los **mensajes de servicio** (las respuestas del negocio dentro de la ventana de 24 h) **por encima de 1.000 mensajes gratis por mes y por número**, sin acumulación. También pasan a cobrarse los mensajes de **utilidad** enviados dentro de la ventana, que eran gratis desde julio de 2025. Si un negocio no tenía medio de pago cargado al 30/09/2026, pueden dejar de entregarse sus mensajes de servicio.
- **Free Entry Point:** si el cliente llega desde un anuncio Click-to-WhatsApp, durante hasta 7 días no se cobra nada, **salvo los mensajes de Meta Business Agent**.
- Argentina es un mercado propio en la tabla de tarifas (código 54). Meta bajó las tarifas de utilidad y autenticación para Argentina el **01/10/2025** y no lista cambios para Argentina en 2026.
- Facturación en pesos: [Data, tier 3] según Cliengo, se puede facturar en **ARS desde el 01/04/2026**. No lo confirmé en Meta.

**Tarifas por mensaje, en USD.** La tabla oficial no se pudo leer directo (es un CSV enlazado), así que crucé fuentes:

| Categoría | Zernio (tabla de Meta del 01/10/2026) | Alibaba Cloud / Wali / Teramont | Gallabox / ManyChat (ene. 2026) | **Decisión** |
|---|---|---|---|---|
| Marketing | 0,0618 | 0,0618 | 0,0711 | **0,0618** |
| Utilidad | 0,0260 | 0,026 (Alibaba cobra 0,0286 = 1,1 × la de Meta) | 0,0299 | **0,0260** |
| Autenticación | 0,0260 | 0,026 | 0,0299 | **0,0260** |
| Servicio (después de los 1.000 gratis) | 0,0260 | 0,0260 (Teramont) | 0,0299 | **0,0260** |

[Estimate] Por qué decido así: 0,0711 / 0,0618 y 0,0299 / 0,0260 dan exactamente **1,15**, lo que sugiere un recargo del 15% de esos revendedores. La tabla vieja de Chatalog (anterior a oct. 2025: 0,07416 / 0,03468) da 1,20 sobre los mismos valores base. Tres fuentes independientes coinciden en 0,0618 y 0,026. **Confianza media-alta.** Hay que verificarlo en la tabla oficial antes del piloto.

**Impacto en el costo de materialIA** [Estimate]. Supuestos: tarifa de servicio USD 0,026; dólar oficial promedio de noviembre 2026 a ARS 1.558 (REM-BCRA); "mensajes" = respuestas del negocio entregadas.

| Escenario por local | Conversaciones/mes × mensajes del bot | Mensajes que se cobran | Costo Meta USD/mes | ≈ ARS/mes |
|---|---|---|---|---|
| Chico | 150 × 6 = 900 | 0 | 0 | 0 |
| Medio | 300 × 6 = 1.800 | 800 | 20,8 | ≈ 32.400 |
| Activo | 600 × 8 = 4.800 | 3.800 | 98,8 | ≈ 153.900 |

Con un precio tentativo de **ARS 70.000/mes (≈ USD 45)**, un local "activo" le costaría a materialIA más en mensajes de Meta que lo que paga. **Esto es nuevo desde el 01/10/2026 y va al pricing:** hay que juntar las respuestas en menos mensajes, poner un tope de mensajes por plan o trasladar el costo. Además, si el comercio usa Meta Business Agent por la API, a unos USD 0,045 por mensaje le sale bastante más caro que la tarifa de servicio.

---

## 3. Inversión y adquisiciones (comercio conversacional, LatAm 2025-2026)

| Fecha | Empresa | Operación | Fuente (tier) |
|---|---|---|---|
| 10/06/2025 | Tiendanube compra **VICI** (AR) | Adquisición. Nace Nuvem Chat / Chat Nube | PitchBook (1), LatamList (2) |
| 2025 | Tiendanube | USD 10M invertidos en IA para Chat Nube | Valora Analitik (2) |
| 03/12/2025 | **Vambe** (Chile) | USD 14M para automatizar el comercio conversacional | SiliconANGLE (2) |
| 27/01/2026 | **Jelou** (Ecuador) | Serie A de USD 10M (Wellington Access Ventures; total USD 13M). IA "transaccional" en WhatsApp. Más de USD 100M procesados y más de 500 clientes | Cronista México (2) |
| sin fecha confirmada | **Pulpos** (México) | USD 5M (Dalus Capital) para IA en WhatsApp para microempresas | Cronista México (2) |
| sin fecha confirmada | **Yalo** | Ampliación de la Serie C en USD 20M | Vocero (3), fecha sin verificar |

**Qué señala** [Opinion]:
1. El capital va a agentes que **cierran transacciones** (pedido, pago, cobranza), que es justo la apuesta de materialIA.
2. Los grandes compran en vez de construir (Tiendanube compró VICI). Una startup argentina con tracción en un nicho vertical es **adquirible**: por plataformas de ecommerce, por software de gestión para corralones o por distribuidores de sanitarios.
3. Las rondas son chicas (USD 5–14M) y regionales. Nadie levantó plata para un vertical de materiales de construcción en AR: el nicho está libre, pero tampoco está validado por inversores.

---

## 4. Construcción y precios

**Actividad (cruce de 3 fuentes):**
- [Data] **Índice Construya, octubre 2026:** −3,53% mensual desestacionalizado, **−9% interanual**, acumulado enero-octubre **−2,3%** contra 2025. Es la **5ª caída mensual seguida**. La empresa dice que la normalización macro y del crédito "están siendo más lentas" de lo esperado, pero ve positivo el mediano plazo para la inversión residencial (Mercado, 06/11/2026, tier 2). Su canasta incluye **sanitarios y grifería**.
- [Data] **ISAC-INDEC, septiembre 2026:** **+5,1% interanual**, +7,8% mensual desestacionalizado, acumulado +1,3% (INDEC, 06/11/2026, tier 1). Viene de agosto: −4,4% interanual (INDEC, 07/10/2026).
  - **Artículos sanitarios de cerámica: −8,2% interanual en septiembre** (−11,4% en agosto).
  - **"Resto", que incluye grifería:** +12,2% interanual en septiembre (+19,4% en agosto).
  - **Superficie autorizada en permisos:** −10,9% interanual (agosto). Puestos de trabajo privados: +1,7% interanual.
  - **Expectativas para oct-dic 2026** (encuesta INDEC): en obra privada, 74% espera que no cambie, 15% que baje y 11% que suba. Los que esperan una baja citan la caída de la actividad económica (28,7%) y la falta de crédito (19%).
- **Las fuentes difieren.** ISAC mide septiembre (+5,1%) y Construya mide octubre (−9%), con distinta cobertura. **Decisión** [Estimate]: la actividad está **estancada o débil, con mucho ruido mes a mes**. El acumulado anual va de −2,3% a +1,3%. Los permisos caen y las empresas no esperan mejora en el trimestre. **La loza sanitaria viene peor que el promedio y la grifería mejor.**

**Inflación y precios:**
- [Data] **IPC septiembre 2026: 1,9% mensual, 23,6% acumulado en el año, 33,4% interanual.** El dato coincide en Canal 26, Diario Panorama, iProUP y DolarHoy (tier 2, citando al INDEC del 13/10/2026). El de octubre sale el **12/11/2026**. Un blog que ya lo da en 2,0% no es oficial y lo descarto.
- [Data] **REM-BCRA (05/11/2026):** octubre 1,8%, noviembre 1,7%, diciembre 1,8%; **2026 cerraría en 30,4%** (otra nota dice 30,6%). Enero-abril 2027: 1,6–1,7% mensual. PBI 2026: +0,7%. Dólar oficial a fin de 2026: ARS 1.590, octubre 2027: ARS 1.985 (Noticias NQN / Perfil, tier 2).
- [Data] **Costo de la construcción (ICC-INDEC), septiembre 2026:** nivel general +1,5% mensual (31,3% interanual), **materiales +1,3% mensual** (22,8% interanual). Entre los grupos que más subieron están los **artículos sanitarios de loza, entre +2,7% y +2,9%** (la tabla del PDF salió desalineada al extraerla) (INDEC, 16/10/2026, tier 1). Rosario: materiales +2,1% mensual promedio en julio 2026 (datos.rosario.gob.ar, tier 1).
- **Cómo actualizan las listas los comercios.** [Data, tier 3] Las fuentes de oficios dicen que los precios de corralón cambian seguido y recomiendan aclarar "precio sujeto a cotización al momento de compra" o cobrar los materiales por adelantado (servidos.ar). [Estimate] Con materiales subiendo 1,3–2% por mes, una lista de precios queda **un 4–6% atrasada en un trimestre**. Eso le da sentido a la regla de materialIA de que un precio vencido pasa a un humano (`requires_human`), y a leer la planilla en vivo. **No hay un dato duro de cada cuánto actualizan su lista los sanitaristas** (ver Data gaps).

**Lectura para materialIA** [Opinion]: con poca demanda, el ferretero tiene **menos ventas y más presión por no perder ninguna consulta**. Es un argumento para "no se te escapa ninguna venta fuera de horario", pero también para que el dueño mire cada peso que gasta. Cobrar en pesos ayuda.

---

## 5. Cambios de comportamiento

- [Data] **Uso de WhatsApp con empresas en AR.** Según un estudio de Meta (citado en Cronista, 18/05/2026, tier 2, **fuente interesada**): 8 de cada 10 argentinos prefieren WhatsApp para contactar empresas; el 74% ya lo usó, la mitad de ellos todos los días o todas las semanas, y el 58% espera respuestas más rápidas que en otros canales. Mercado (27/11/2025, tier 2, sin fuente primaria) da **86%**. **Decisión:** 74–86% de adopción; uso **[Data] alto, confianza media** por el sesgo de las fuentes.
- [Data] Los argentinos abren WhatsApp **37 veces por día**, casi el doble del promedio mundial. WhatsApp llega al 93,5% de los internautas mayores de 16 años (Noticias NQN, 29/10/2026, tier 2; Statista da 93,3% para 2T 2025, tier 1).
- **Ferreterías que venden por WhatsApp.** Sólo encontré un **proxy de Perú**: el 80% de las ferreterías minoristas vende por WhatsApp y el 87% pide mercadería por ese canal (Xplora/Grupo Lucky, Gestión, 29/06/2022, tier 2, **VIEJO y de otro país**). En Argentina, CAFARA representa más de 5.000 ferreterías (dato de 2020, VIEJO). [Assumption] En AR la proporción es parecida o mayor, por la penetración de WhatsApp.
- **Audios.** No hay cifra argentina. [Data] Chat Nube ya interpreta audios e imágenes (iProUP, tier 2) y WhatsApp transcribe audios de forma nativa. [Opinion] Que el agente entienda **audios y fotos de listas escritas a mano es requisito básico**, no un diferencial.
- **Plomeros y arquitectos que cotizan por lista.** No hay dato cuantitativo. [Data, tier 3] servidos.ar dice que dar precios "de palabra o por WhatsApp sin estructura" es un error común de los oficios y recomienda presupuestos escritos con materiales separados de la mano de obra. [Opinion] Eso coincide con la funcionalidad de "cotizar listas de materiales de obra": el profesional necesita un presupuesto prolijo que pueda reenviar a su cliente.
- [Data] Ecommerce AR, 1er semestre 2026: facturación ≈ ARS 19,5 billones, **+28% interanual**, y órdenes +21% (CACE vía Mercado e iProUP, tier 2). Ecosistema Startup describe a WhatsApp como un canal donde ya se muestra catálogo, se cobra y se atiende la posventa (tier 3).

---

## 6. Predicciones (2027 y después)

- [Data, Gartner, tier 1, jun. 2025] **Más del 40% de los proyectos de IA agéntica se cancelarán antes de fin de 2027** por costos, valor poco claro o falta de control de riesgos. Gartner estima que sólo unos 130 de miles de proveedores son agentes de verdad (el resto hace "agent washing"). Para materialIA es un riesgo de reputación del rubro: el comprador va a desconfiar de "agentes de IA" que no cumplen.
- [Data, Gartner, tier 1, 10/09/2025] Para 2028, ninguna empresa del Fortune 500 habrá eliminado del todo la atención humana. Para 2027, la mitad de las que planeaban recortar personal por IA abandonarán ese plan. Valida el modelo "IA + derivación a humano".
- [Data, Gartner, VIEJO, mar. 2025] La IA agéntica resolvería el 80% de los problemas comunes de atención para 2029. Para 2028, el 70% de los recorridos de atención empezarían y terminarían en asistentes conversacionales de terceros (CX Today, tier 2).
- [Data, REM-BCRA, 05/11/2026] Inflación de 1,6–1,7% mensual en el 1er cuatrimestre de 2027 (≈ 20–22% anualizado). Expectativa a 12 meses: 21,9%. Crecimiento débil, con riesgo de recesión técnica en el 3T 2026. **No hay un número anual del REM para 2027 en las fuentes que leí.**
- [Data, Construya, 06/11/2026] El mediano plazo sería positivo para la inversión residencial "si la superficie autorizada se traduce en obras". Pero los permisos caen −10,9% interanual (INDEC).
- [Data, Meta, 2026] Hoja de ruta anunciada: plataforma de agentes para empresas con conectores (Shopify, Zendesk, Shopee), Business Discovery, informes diarios de los chats de la noche. **No hay fecha para pagos en Argentina.**
- [Opinion] Para 2027, lo más probable es que "responder por WhatsApp con IA" sea gratis o casi (Meta). El valor se corre a **conectar con el inventario y el precio reales, armar listas o presupuestos y cobrar de forma verificada**, sobre todo en rubros técnicos con miles de códigos, como sanitarios y grifería.

---

## 7. Evaluación del momento

| Factor | Señal | Peso |
|---|---|---|
| Hábito del canal (WhatsApp con comercios) | Muy favorable, ya masivo | Alto |
| Validación del formato "agente que cobra en el chat" (Tiendanube/VICI, Jelou, Vambe) | Favorable | Medio |
| Meta Business Agent gratis o barato dentro de la app | Desfavorable para lo básico; neutro para stock, pedido y cobro | Alto |
| Pagos nativos de WhatsApp en AR | Todavía no existen. Hay ventana | Medio |
| Costo de la API desde el 01/10/2026 (servicio pago después de 1.000) | Desfavorable para el margen | Medio |
| Demanda de construcción (Construya −9% interanual, permisos −10,9%, loza −8,2%) | Desfavorable | Medio |
| Inflación de 1,7–1,9% mensual: listas que se atrasan | Favorable al dolor "precio actualizado" | Medio |
| Competencia en pesos y sin tienda online | Casi vacía (ver competitors.md) | Alto |

**Veredicto** [Opinion, confianza media]: **neutro tirando a bueno.** La tecnología y el hábito están maduros y el nicho (sin tienda, con planilla, en pesos, cotización técnica) sigue libre. Pero hay una **ventana de unos 12–18 meses** antes de que Meta o Tiendanube bajen el "cierre en el chat" a comercios sin tienda, y la demanda de obra está floja. Conviene entrar ahora, **chico y por WhatsApp**, para conseguir casos y datos del rubro antes de que se cierre la ventana, con un precio que cubra los mensajes de Meta en locales de mucho volumen.

---

## 8. Data gaps

1. **Tabla oficial de tarifas de Meta para AR en ARS y USD.** Probé 3 formulaciones de búsqueda y crucé 5 fuentes de terceros. Para cerrarlo: bajar el CSV desde developers.facebook.com/docs/whatsapp/pricing (sección rate cards) o mirar la facturación del WABA del piloto.
2. **Cuota de Business Agent en cada plan de Meta One y precio en ARS.** Meta no la publica. Para cerrarlo: abrir la suscripción desde una cuenta de WhatsApp Business argentina y capturar la pantalla.
3. **Si Business AI lee stock o arma pedidos en AR.** Ninguna fuente lo afirma. Lo único que hay es una negación de Tiendanube, que es fuente interesada. Para cerrarlo: configurar una cuenta de prueba con catálogo y hacer 10 consultas de stock.
4. **Fecha de los pagos de WhatsApp en Argentina.** No hay anuncio oficial. Para cerrarlo: alerta en el newsroom de Meta y de Mercado Pago, y consultar el registro de PSP del BCRA.
5. **Porcentaje de ventas por WhatsApp en ferreterías y sanitarios de AR.** Probé 3 formulaciones (CACE, CAFARA, ferreterías + WhatsApp). Sólo está el proxy de Perú de 2022. Para cerrarlo: encuesta de 5 preguntas a 30 locales de CABA durante el descubrimiento, o pedirle el dato a CAFARA.
6. **Uso de audios para pedir materiales.** No hay dato de AR. Para cerrarlo: contar en los chats del piloto qué proporción de mensajes entrantes son audio o foto.
7. **Cada cuánto actualizan las listas los sanitaristas.** No hay dato. Para cerrarlo: preguntarlo en las entrevistas y pedir el historial de versiones de la planilla del piloto.
8. **IPC de octubre 2026** (sale el 12/11/2026) e **inflación anual 2027 del REM**. Para cerrarlo: indec.gob.ar y bcra.gob.ar/REM.
9. **ICC de septiembre: valor exacto de "griferías y llaves de paso"** (la tabla del PDF salió desalineada). Para cerrarlo: Cuadro 3 del PDF del ICC o los cuadros web del INDEC en Excel.
10. **Fechas de las rondas de Pulpos y Yalo.** Para cerrarlo: Crunchbase o LAVCA.

---

## 9. Fuentes

**Tier 1**
- Meta for Developers, precios de la WhatsApp Business Platform: https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing (consultada 09/11/2026)
- INDEC, ISAC septiembre 2026 (06/11/2026): https://www.indec.gob.ar/uploads/informesdeprensa/isac_11_26F4E69BED3F.pdf
- INDEC, ISAC agosto 2026 (07/10/2026): https://www.indec.gob.ar/uploads/informesdeprensa/isac_10_2674E79F6A29.pdf
- INDEC, ICC septiembre 2026 (16/10/2026): https://www.indec.gob.ar/uploads/informesdeprensa/icc_10_26C96DA2A124.pdf
- Rosario, índices de materiales julio 2026: https://datos.rosario.gob.ar/sites/default/files/2026-08/07_26%20Informe%20indices%20mat%20de%20la%20construccion.pdf
- Gartner, Fortune 500 y atención humana (10/09/2025): https://www.gartner.com/en/newsroom/press-releases/2025-09-10-gartner-predicts-none-of-the-fortune-500-companies-will-have-fully-eliminated-human-customer-service-by-2028
- PitchBook, Tiendanube: https://pitchbook.com/profiles/company/90805-78
- Statista, redes sociales en AR: https://www.statista.com/statistics/1313074/social-networks-penetration-argentina

**Tier 2**
- Cronista, Business AI en pymes (18/05/2026): https://www.cronista.com/infotechnology/it-business/asi-funciona-la-novedad-de-whatsapp-que-usan-las-pymes-para-vender-mas-sin-sumar-personal/
- TechCrunch, Meta Business Agent global (03/06/2026): https://www.techcrunch.com/2026/06/03/metas-ai-agent-for-whatsapp-business-is-now-available-globally/
- Culturageek, Meta One (16/09/2026): https://culturageek.com.ar/meta-one-precios-planes/
- Expansión, Meta One (15/09/2026): https://expansion.mx/tecnologia/2026/09/15/meta-one-precios-funciones-whatsapp-instagram-facebook
- Mercado, Construya octubre (06/11/2026): https://mercado.com.ar/ladrillos-y-proyectos/el-indice-construya-cayo-353-en-octubre-y-bajo-9-interanual
- Mercado, Tiendanube y Meta en AR (08/12/2025): https://mercado.com.ar/innovacion/tiendanube-y-meta-habilitan-ventas-automatizadas-por-whatsapp-en-argentina-por-primera-vez
- iProUP, Chat Nube arma el carrito y cobra: https://www.iproup.com/innovacion/62792-tiendanube-integra-ventas-automaticas-en-whatsapp-la-ia-ahora-arma-el-carrito-y-cobra
- Mercado, Chat Nube suma Instagram: https://mercado.com.ar/ruta-digital/tiendanube-suma-instagram-a-chat-nube-y-amplia-su-estrategia-de-comercio-conversacional
- LatamList, Tiendanube compra VICI: https://latamlist.com/?p=17297
- Descubre.vc, VICI (17/06/2025): https://www.descubre.vc/noticia/tiendanube-adquiere-vici-y-lanza-nuvem-chat-en-latam-2025-06-17
- Valora Analitik, USD 10M de Tiendanube en IA: https://www.valoraanalitik.com/tiendanube-invierte-millones-solucion-ia/
- Cronista México, Jelou (27/01/2026): https://www.cronista.com/mexico/finanzas-economia/llega-startup-de-ia-transaccional-jelou-levanta-10-mdd-para-operar-pagos-en-whatsapp
- Cronista México, Pulpos: https://www.cronista.com/mexico/finanzas-economia/pulpos-recauda-5-millones-de-dolares-para-revolucionar-pymes-mexicanas-con-ia-en-whatsapp
- SiliconANGLE, Vambe (03/12/2025): https://siliconangle.com/?p=723195
- DPL News, asistente IA de Mercado Pago: https://dplnews.com/mercado-pago-lanza-su-asistente-ia-en-argentina-para-transferir-pagar-e-invertir-por-texto-o-voz/
- iProUP, pagos agénticos (ago. 2026): https://www.iproup.com/finanzas/70397-mercado-libre-tiendanube-y-tarjetas-ya-prueban-compras-agenticas-en-argentina.amp
- Canal 26, IPC septiembre 2026 (13/10/2026): https://www.canal26.com/economia/2026/10/13/la-inflacion-de-septiembre-fue-de-19-y-acumula-un-alza-de-236-en-lo-que-va-del-2026/
- Diario Panorama, IPC septiembre: https://diariopanorama.com/noticia/569591/indec-confirmo-inflacion-septiembre-fue-19porciento-acumula-334porciento-doce-meses
- Noticias NQN, REM (05/11/2026): https://www.noticiasnqn.com.ar/noticias/2026/11/05/359748-el-rem-proyecto-una-inflacion-del-30_4por_ciento-para-2026-segun-las-consultoras
- Noticias NQN, 37 aperturas diarias de WhatsApp (29/10/2026): https://www.noticiasnqn.com.ar/noticias/2026/10/29/358767-los-argentinos-abren-whatsapp-37-veces-por-dia-casi-el-doble-que-el-promedio-mundial
- Mercado, WhatsApp y ecommerce 2025 (27/11/2025): https://mercado.com.ar/ruta-digital/el-comercio-electronico-argentino-crece-79-en-2025-y-whatsapp-transforma-la-relacion-comercial
- Mercado, CACE 1er semestre 2026: https://mercado.com.ar/tendencias/cace-el-comercio-electronico-facturo-19-533-815-millones-en-el-primer-semestre
- Gestión (Perú), ferreterías y WhatsApp (29/06/2022, VIEJO): https://gestion.pe/economia/empresas/uso-de-billeteras-electronicas-en-ferreterias-ya-duplica-a-tenencia-de-pos-empresas-noticia/
- The Star / Reuters, Gartner 40% (25/06/2025): https://www.thestar.com.my/tech/tech-news/2025/06/25/over-40-of-agentic-ai-projects-will-be-scrapped-by-2027-gartner-says
- CX Today, Gartner 80% para 2029 (VIEJO): https://cxtoday.com/contact-center/agentic-ai-gartner-predicts-80-of-customer-problems-solved-without-human-help-by-2029

**Tier 3**
- Cliengo, guía Meta Conversations 2026 (09/10/2026): https://guiawabusiness.cliengo.com/meta-conversations-2026
- Cliengo, pagos por WhatsApp: https://guiawabusiness.cliengo.com/whatsapp-payments
- Zernio, tabla de tarifas (01/10/2026): https://zernio.com/whatsapp-api-pricing
- Gallabox, tabla de tarifas: https://docs.gallabox.com/pricing-and-billing/whatsapp-pricing/rate-card.md
- Alibaba Cloud, facturación de ChatApp: https://www.alibabacloud.com/help/en/chatapp/product-overview/billing-overview
- Wali, tabla de precios: https://app.wali.chat/help/pricing-table
- ManyChat, precios: https://help.manychat.com/hc/en-us/articles/14281380243740
- Chatalog, tarifas anteriores a oct. 2025: https://chatalog.ai/en/pricing-whatsapp-conversation-fees/
- Ecosistema Startup, ecommerce AR y el chat como canal: https://ecosistemastartup.com/e-commerce-argentina-1815m-ordenes-y-el-chat-como-canal/
- servidos.ar, presupuestos de oficios: https://servidos.ar/blog/como-armar-presupuesto-profesional-oficios-argentina
