# C3 — Perfil del público objetivo (materialIA)

> **Insumo original de investigación, 09/11/2026.** Se conserva como antecedente, sin certificar sus afirmaciones. Para decisiones usar las síntesis y [correcciones posteriores](../corrections-2026-11-09.md); las tarifas de servicio de Meta y sus escenarios derivados quedaron retirados.

Fecha: 09/11/2026 · Agente C3 · Alcance: comercios de sanitarios, grifería, mamparas y ferretería en CABA (fase 1) y mayoristas (fase 2).

**Etiquetas:** [Data] = dato con fuente · [Estimate] = cálculo propio sobre datos · [Assumption] = supuesto razonable sin fuente directa · [Opinion] = juicio del analista.
**Tiers de fuente:** T1 = oficial/primaria (GCBA, ARCA, BCRA, cámara) · T2 = medio periodístico o publicación sectorial · T3 = blog/directorio/marketing.
Todo el contenido web se tomó como dato no confiable; los números se cruzaron cuando se pudo.

---

## 0. Hallazgo clave: el mapa real de CABA (Relevamiento de Usos del Suelo 2022–2024, GCBA)

Bajé el CSV oficial del RUS (GCBA, 381.000 registros por parcela, relevados entre 2022 y 2024, publicado en oct-2025) y filtré por rubro. [Data, T1]

| Rubro (campo TIPO2, estado ACTIVO) | Locales en CABA |
|---|---|
| Ferretería | **1.181** |
| Sanitarios + venta de art. sanitarios + art. plomería y gas + plomería | **390** (283 + 42 + 35 + 30) |
| Materiales para la construcción (corralones) | 265 |
| Vidriería + vidrios y espejos (son los que suelen hacer mamparas) | 305 (259 + 46) |
| Materiales eléctricos | 156 |
| Cerámicas | 80 |
| Pinturería | 411 |

- Los ~475 potenciales que se estimaron antes son coherentes con 390 sanitarios/plomería más una parte de los corralones. [Estimate]
- Límites: el RUS releva usos **por parcela**, así que una galería o un local con varios rubros puede quedar subcontado; tampoco distingue minorista de mayorista. [Data/limitación]

---

## 1. Persona principal: "Claudio", dueño de una casa de sanitarios de corredor

> Persona compuesta [Assumption], armada con los datos de abajo. Hay que validarla con 15–20 entrevistas en la calle.

| Campo | Detalle |
|---|---|
| Rol | Dueño y encargado. Atiende el mostrador, compra a los proveedores y contesta el WhatsApp. |
| Comercio | Casa de sanitarios y grifería sobre Av. Juan B. Alberdi (Floresta/Vélez Sarsfield). Vende inodoros, depósitos, griferías FV/Peirano, flexibles, termotanques y cañería. Tiene 29 competidores a menos de 5 cuadras. [Data: RUS] |
| Equipo | 2 a 5 personas: él, un hijo o sobrino y 1 a 3 vendedores. El 66% de los comercios ferreteros encuestados por CAFARA tiene hasta 5 empleados. [Data, T2: Revista Ferreteros/CAFARA, mar-2026, n=47] |
| Edad / generación | 45–60 años, segunda generación. El hijo de 25–35 es el que empuja la parte digital. El cambio generacional y la incorporación de software y WhatsApp/Instagram los traen "las nuevas generaciones". [Data cualitativo, T2: Messe Frankfurt/CAFARA, jul-2023] La edad puntual es [Assumption] y es un **DATA GAP**. |
| Categoría fiscal | Mezcla de monotributo alto (categorías I a K) y responsable inscripto. Una casa de sanitarios de corredor con 3+ empleados probablemente supera el tope de K. [Assumption] El tope de K es ≈ $126,6 M/año desde el 1/8/2026, unos $10,5 M/mes. [Data, T2: iProfesional, sep-2026] Los ARS 70.000/mes equivalen al 0,66% de esa facturación mensual. [Estimate] |
| Factura electrónica | Es obligatoria para todos los monotributistas y responsables inscriptos (ARCA). [Data conocido; no lo re-verifiqué en esta ronda] |
| SKU | Entre algunos cientos y ~3.000 artículos activos. [Assumption] Una ferretería promedio tiene "20.000 o más artículos". [Data, T2: CAFARA vía Messe, 2023] Una casa de sanitarios es mucho más acotada, y por eso encaja mejor en Google Sheets. [Opinion] |
| Stock y precios | Usa listas de los proveedores en Excel/PDF, aplica un coeficiente y lleva un sistema de gestión en la PC del mostrador (Tango, Líder, Dux u otro de los "de siempre") o directamente cuaderno + Excel. [Assumption] Dux maneja varias listas de precios en $ y US$ y sincroniza stock. [Data, T3] Líder Gestión vende licencia perpetua sin cuota mensual. [Data, T3] **DATA GAP:** no hay cuota de mercado de sistemas en ferreterías/sanitarios. |
| Cobros | Efectivo, transferencia, QR de Mercado Pago y débito/crédito con posnet. El 98,6% de los pagos con transferencia interoperables (PCT) se inician con QR y crecieron 40,7% interanual en 2025. [Data, T1: BCRA, Informe de Pagos Minoristas] **DATA GAP:** no hay mix de cobros específico del rubro. |
| Objetivos | 1) No perder ventas en un año malo. 2) Contestar rápido al plomero o a la señora que manda foto del depósito roto. 3) Dejar de pasarse la noche cotizando listas de obra. 4) Mantener el margen con aumentos de proveedores. |
| Frustraciones | Las ventas vienen cayendo: 71,4% de las ferreterías vendió menos en los últimos 3 meses y al 44,3% la caída le superó el 10%. [Data, T2: informe CAFARA vía Rosario3/Ecos365, sep-2026] El ticket bajó (57,1%). El WhatsApp no para y tiene que contestarlo él. Las listas de proveedores cambian y no da abasto para actualizar. Los clientes "no saben el nombre de lo que buscan". [Data cualitativo, T2: CAFARA 2023] |
| Herramientas | WhatsApp Business en un celular compartido, Excel, sistema de gestión, Mercado Pago, Instagram (lo maneja el hijo). [Assumption] |
| Cita representativa | No conseguí una cita textual de un dueño de sanitarios en CABA (**DATA GAP**). La más cercana es del presidente de CAFARA: *"el ferretero no es solo un vendedor, es un coach"* (S. Angiulli, 2023). Esa frase resume el miedo central: que un bot "no asesore como yo". |

---

## 2. Comportamiento de compra

**Cómo descubren herramientas** [mayormente Assumption + señales T2]
1. Otro comerciante del mismo corredor ("¿qué usás vos?"). La densidad sobre Alberdi hace que el boca a boca sea muy rápido. [Opinion]
2. El hijo o sobrino que ve algo en Instagram/YouTube.
3. El vendedor del mayorista o del proveedor que pasa todas las semanas (hay avisos de "vendedor viajante para distribuidora mayorista de ferretería" en Bumeran y Computrabajo). [Data, T3]
4. El contador, sobre todo para facturación y sistema de gestión, no para ventas. [Assumption]
5. CAFARA y Revista Ferreteros: los socios piden capacitación en "ventas por WhatsApp con seguimiento", "chatbots" e "introducción a IA". [Data, T2: Encuesta de capacitación CAFARA 2026]

**Quién decide:** el dueño, sin comité. El hijo o sobrino es el que influye y el que va a usar la herramienta. [Assumption]

**Criterios, en orden** [Opinion]
1. Que **no se equivoque** con un repuesto o un precio (si se equivoca, hay devoluciones y pierde clientes).
2. Que le ahorre tiempo de verdad en cotizar y en contestar fuera de horario.
3. Precio en pesos, mensual y sin contrato largo.
4. Que no le exija cargar todo de nuevo (que tome su lista o su sistema).
5. Que alguien vaya al local si algo falla.

**Presupuesto:** no hay dato del gasto en software del rubro (**DATA GAP**). Referencias: WhatsApp Business App es gratis, Meta Business AI viene integrado (costo no informado), Prometheo ofrece un CRM con IA a US$50. [Data, T2: Cronista, may-2026] Los ARS 70.000/mes compiten contra "gratis" y contra el sueldo parcial de un empleado. [Opinion]

**Tiempo de decisión:** [Assumption]
- Corredor con referencia de un vecino: 1 a 3 visitas, entre 1 y 3 semanas.
- Sin referencia: más de 1 mes. Lo más probable es "volvé el mes que viene".
- Mayorista: 1 a 3 meses y suma a más gente (encargado de ventas, sistemas).

**Objeciones probables, de más a menos frecuente** [Opinion basada en datos]
1. **"WhatsApp ya lo contesto yo / Meta ya me da un bot gratis."** Business AI de Meta llegó primero a Argentina (may-2026). [Data, T2] Respuesta: materialIA lee stock y precio reales, cotiza listas, arma el pedido y cobra con Mercado Pago. El bot de Meta se entrena con el catálogo pero no lee stock ni cobra. [Data, T2: Cronista]
2. **"No tengo precios ni stock al día en una planilla."** Es el prerrequisito del producto. Con aumentos frecuentes de proveedores, sostener la planilla es trabajo. Respuesta: la instalación incluye la migración inicial y un proceso simple de "pegá la lista del proveedor".
3. **"Con cómo están las ventas no puedo pagar $70.000."** El 71,4% vende menos. [Data, T2] Respuesta: primer mes gratis o pago contra ventas cobradas por el link.
4. **"Mis clientes quieren hablar conmigo / el bot va a recomendar mal."** Es la identidad del ferretero-asesor. Respuesta: derivación a humano y que el bot cotice pero no "diagnostique".
5. **"¿Y si ustedes dejan de existir?"** Desconfianza hacia dos estudiantes. Respuesta: sin permanencia, número de WhatsApp a nombre del comercio y la planilla queda en su Drive.

---

## 3. Día típico del dueño/encargado [Assumption; DATA GAP de fuente directa]

| Franja | Qué pasa |
|---|---|
| 7:30–8:30 | Abre. Vienen plomeros y gasistas antes de ir a la obra. Es el **pico 1**: ventas rápidas, "¿tenés tal flexible?". |
| 9–12 | Mostrador con particulares, recibe mercadería y atiende a los viajantes de los proveedores. El WhatsApp se acumula. |
| 12–16 | Baja el ritmo (algunos cierran al mediodía). Contesta los WhatsApp atrasados y cotiza listas de obra. |
| 16–19 | **Pico 2**: particulares que salen del trabajo. |
| 19–23 | Desde la casa: contesta WhatsApp, actualiza precios con la lista nueva del proveedor y arma presupuestos. |
| Sábado 8–13 | Pico de particulares (arreglos del hogar). |

Lo que le roba tiempo, en orden [Opinion]: (1) cotizar listas de obra producto por producto, (2) actualizar precios por aumentos, (3) contestar "¿tenés?" y "¿cuánto sale?" por WhatsApp, (4) mandar alias o CBU y verificar transferencias.
El 93,8% de las ferreterías encuestadas trabaja a tiempo completo y el 84,6% opera solo de forma presencial. [Data, T2: CAFARA 2023-24, n≈30, con bases inconsistentes]

---

## 4. Persona secundaria: "Mariana", 2.ª generación en un corralón o ferretería grande de barrio

- 30–40 años, hija del fundador. Maneja compras, Instagram y el WhatsApp del local. El padre sigue en el mostrador. [Assumption]
- Corralón de materiales (265 en CABA; clusters en Av. Olivera 500 en Parque Avellaneda, Av. Juan B. Justo 5500 en Villa Santa Rita y Av. Chiclana 4000 en Nueva Pompeya). [Data: RUS] O ferretería grande con sanitarios.
- Recibe listas de obra de constructores por foto o audio. Le interesa la **cotización automática y el link de pago** más que el asesoramiento.
- Ya usa un sistema de gestión (Dux/Tango). Va a exigir que el bot lo lea o que la sincronización sea fácil, porque no quiere mantener una planilla duplicada. [Assumption]
- Es la que **decide más rápido** y la que más va a recomendar el producto. Es la "champion" ideal aunque el dueño firme. [Opinion]

---

## 5. Anti-persona (a quién NO venderle ahora)

1. **Ferretería de barrio chica de dueño solo, 60+, con cuaderno.** Tiene más de 20.000 artículos de bajo ticket (tornillería y fijaciones son lo que más se vende [Data, T2: CAFARA 2026]), venta fraccionada y presencial, ninguna lista digital y poca venta por WhatsApp. No hay planilla que leer: la instalación sería eterna y el valor, bajo. Además es el segmento más castigado por la caída. Representa el **72,9%** del sector ("ferreterías de barrio"). [Data, T2] **Es la mayoría del mercado y es la peor para empezar.**
2. **Cadenas y grandes showrooms** (Barugel Azulay, Sione, Blaisten, Easy/Sodimac). Tienen e-commerce, IT propio y compras corporativas. No compran a dos estudiantes que van caminando. [Opinion]
3. **Fábricas de mamparas 100% a medida** sin productos estándar. El "stock" no existe: todo es medida → presupuesto → fabricación. El bot solo serviría para pre-calificar y pedir medidas. Encaje bajo hasta que haya un módulo de presupuesto paramétrico. [Opinion]

---

## 6. Encaje por segmento

| Segmento | Cantidad en CABA [RUS] | SKU / complejidad | Venta por chat | Ticket | Encaje con materialIA | Nota |
|---|---|---|---|---|---|---|
| **Casa de sanitarios/grifería minorista** | ~390 (con plomería) | Acotado y estándar (marcas FV, Ferrum, Peirano) | Alta (fotos de repuestos, listas de obra de plomeros) | Medio-alto | **ALTO** ★ | Combos naturales (inodoro + depósito + asiento + flexible). Están concentrados en corredores. |
| Corralón / materiales | 265 | Medio, con precios volátiles | Alta (listas de obra de constructores) | Alto | Medio-alto | Pide flete y cuenta corriente, que hoy no se cubren. Bueno como fase 1.5. |
| Cerámicas (pegadas a sanitarios) | 80 | Medio (m² y cajas) | Media | Alto | Medio | Están en el mismo corredor de Alberdi: se suman en la misma caminata. |
| Ferretería de barrio | 1.181 | Muy alto (20.000+) y fraccionado | Media-baja | Bajo | **BAJO-MEDIO** | Solo sirven las grandes con sistema y planilla. Evitar las chicas. |
| Vidriería / mamparas | ~305 | Hecho a medida | Media (pedido de presupuesto) | Alto | Bajo (hoy) | Necesita un cotizador por medidas, no stock. |
| Mayorista/distribuidor | DATA GAP (el RUS no distingue) | Muy alto, con listas por cliente | Alta (pedidos de comercios) | Muy alto | Alto valor, **fase 2** | Ciclo largo, B2B, cuenta corriente, integración con ERP. También sirven como canal. |

---

## 7. Zonas de CABA para recorrer (datos del RUS 2022-24, conteo propio)

**Top 3 para arrancar:**

1. **Av. Juan Bautista Alberdi 3400–3999 (Floresta / Vélez Sarsfield / Parque Avellaneda): EL corredor de sanitarios de CABA.** En esos 6 tramos de cuadra hay **29 sanitarios + 16 cerámicas + 1 venta de artículos sanitarios = 46 comercios** del rubro. Hay que sumar las transversales Mariano Acosta (7 del rubro) y Martínez Castro (5), y seguir por Alberdi 2900–3100 y 4000–4999 (otros ~22 entre sanitarios, cerámicas, corralones y vidrierías). **Son unos 70 comercios en ~2 km.** [Data: RUS + Estimate] Es ideal para el efecto vecino: si cierran 1 o 2 en un corredor, se lo cuentan al resto.
2. **Once / Balvanera.** Es el barrio con más sanitarios (32): Jean Jaurès 50–478 (5), Rincón 25–51 (3), Junín 168–278, Av. Corrientes 2900–3400 (3), Av. Rivadavia 2100–3300 (3) y Av. Belgrano. Además hay **74 ferreterías**, con un cluster en Pasteur 0–499 (8), probablemente mayoristas (eso es [Assumption]). Sirve para probar minoristas y detectar mayoristas para la fase 2.
3. **Eje Flores – Caballito – Villa Crespo.** Av. Gaona 3000–3499 (3 sanitarios + 2 ferreterías + corralón + vidriería), Donato Álvarez 0–499 (9 del rubro), Av. Rivadavia y, más al norte, **Villa Crespo** (110 comercios del rubro: Av. Warnes 500s con 5 ferreterías, Av. San Martín 1500s con 6, Av. Corrientes 4500s con 5).

**Para después (corralones, persona secundaria):** Av. Olivera 500–999 en Parque Avellaneda (9 corralones), Av. Juan B. Justo 5500–5999 en Villa Santa Rita (9), Av. Chiclana 4000s en Nueva Pompeya (6), Av. Eva Perón 5000s en Lugano/Mataderos (6), Av. Rivadavia 10500s en Liniers (6).

**Barrios con más comercios del rubro (todos los rubros relevantes):** Palermo 138, Balvanera 126, Villa Crespo 110, Recoleta 99, Flores 99, Belgrano 93, Almagro 93, Caballito 93, Mataderos 81, Villa Urquiza 77. Palermo, Recoleta y Belgrano tienen mucho comercio pero disperso y más showrooms o cadenas. [Data RUS + Opinion]

> Nota: "Av. Warnes" se conoce más por autopartes; en el RUS aparece con 10 ferreterías, pero no es un corredor de sanitarios. Sobre "Av. Juan B. Justo" hay que aclarar que el corredor fuerte es de corralones (Villa Santa Rita) y no de sanitarios: el corredor de sanitarios es **Alberdi**, no Juan B. Justo.

---

## 8. Dónde encontrarlos

| Canal | Densidad de público objetivo | Costo | Notas |
|---|---|---|---|
| Caminata por corredor (Alberdi, Once) | **Muy alta** (46 en 6 cuadras) | Solo tiempo | Canal principal. Conviene ir de 10 a 12 o de 13 a 16, fuera de los picos. [Assumption] |
| Referidos entre vecinos de corredor | Alta | Descuento o mes gratis | En corredores competitivos, mostrar "lo usa el de enfrente" puede tanto ayudar como trabar. Pedir permiso para mostrarlo. [Opinion] |
| Mayoristas/distribuidores (p. ej. Sanitarios Hidro en Liniers, que dice abastecer a ferreterías y corralones [Data, T3: servidos.ar]; MaxiFer; Ferretería General Paz) | Alta (cada uno tiene cientos de clientes) | Revenue share o comisión | Son a la vez canal y cliente de la fase 2. Sus viajantes visitan cada semana. [Data T3: avisos de empleo] |
| Proveedores/fabricantes (vendedores de zona de FV, Ferrum, Peirano) | Alta | Alianza | **DATA GAP:** no se verificó que tengan programas para comercios. [Assumption] |
| CAFARA (~300 socios, sede Lavalle 1646) + Revista Ferreteros | Media (más ferreterías del interior que sanitarios de CABA) | Bajo (nota, capacitación) | Los socios piden capacitación en WhatsApp, chatbots e IA. [Data T2] Posibilidad: dar una charla o webinar. |
| Día del Ferretero (3/9) y eventos CAFARA | Media | Bajo | El de 2026 fue en Rosario. ExpoFerretera recién en 2027. |
| Grupos de Facebook/WhatsApp de ferreteros | DATA GAP | Gratis | No encontré grupos verificables. Hay que buscarlos a mano en Facebook. |
| Cámara específica de sanitarios en CABA | DATA GAP | — | No encontré ninguna (CACOSA no aparece). |
| Software de gestión (Dux, Líder, Tango) y sus revendedores | Media | Integración o partnership | Riesgo y oportunidad: cada sistema podría sacar su propio bot. |

---

## 9. Data gaps

- Edad, género y nivel de estudios de los dueños de sanitarios/ferreterías (no hay encuesta pública).
- Mix fiscal (monotributo vs responsable inscripto) por rubro y facturación típica de una casa de sanitarios de CABA.
- Cuota de mercado de los sistemas de gestión (Tango, Líder, Dux, Vendi, Bind, etc.) en el rubro.
- Porcentaje de ventas que entra por WhatsApp y volumen de mensajes por día de un comercio típico.
- Mix de medios de cobro del rubro (QR de Mercado Pago vs transferencia vs efectivo).
- Horarios y picos reales (todo el bloque 3 es supuesto).
- Grupos de Facebook/WhatsApp de ferreteros y cámara de sanitarios de CABA.
- Cuántos de los 390 "sanitarios" del RUS son mayoristas.
- Costo y capacidades reales de Meta Business AI en Argentina (si lee stock y precios o si cobra).
- **Acción sugerida:** 20 entrevistas de 10 minutos sobre Alberdi y en Once para cerrar edad, sistema, volumen de WhatsApp, precio aceptable y objeciones.

---

## 10. Fuentes

| # | Fuente | Fecha | Tier | Uso |
|---|---|---|---|---|
| 1 | [GCBA — Relevamiento de Usos del Suelo 2022-2024 (CSV)](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/relevamiento-usos-suelo/relevamiento-usos-del-suelo-2022-2024.csv) · [documentación](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/relevamiento-usos-suelo/documentacion-relevamiento-usos-suelo-2022-2024.pdf) | 2022-24 (publicado oct-2025) | T1 | Conteos por rubro, barrio y calle (análisis propio) |
| 2 | [Messe Frankfurt / CAFARA — "Cambio generacional" (gacetilla)](https://expoferretera.ar.messefrankfurt.com/content/dam/messefrankfurt-argentina/expoferretera/press-releases/2023/02EF2023_JUL2023_Cambio_generacional-sector_ferretero.pdf) | jul-2023 | T2 | 15.000 ferreterías, 80% consumidor final, 20.000+ artículos, cambio generacional |
| 3 | [Revista Ferreteros — Encuesta de capacitación CAFARA 2026](https://revistaferreteros.com.ar/en/encuesta-de-capacitacion-ferretera-2026/) | 18/03/2026 | T2 | 66% hasta 5 empleados; demanda de WhatsApp, chatbots e IA |
| 4 | [Rosario3/Ecos365 — Día del Ferretero, informe CAFARA](https://www.rosario3.com/ecos365/noticias/dia-del-ferretero-121-anos-de-historia-en-medio-de-la-peor-caida-de-ventas-del-sector-20260903-0004.html) | 03/09/2026 | T2 | Caída de ventas, 72,9% de barrio, tornillería |
| 5 | [Revista Ferreteros — Encuesta CAFARA a ferreterías](https://revistaferreteros.com.ar/encuesta-cafara-a-ferreterias/) | 30/04/2024 | T2 | 84,6% presencial (muestra chica e inconsistente) |
| 6 | [Revista Ferreteros — Venta online en el comercio minorista ferretero](https://revistaferreteros.com.ar/en/venta-online-comercio-minorista-ferretero/) | 25/08/2026 | T2 | Ventas online de pymes +14,9% interanual (CAME, jul-2026) |
| 7 | [Cronista — Business AI de WhatsApp para pymes](https://www.cronista.com/infotechnology/it-business/asi-funciona-la-novedad-de-whatsapp-que-usan-las-pymes-para-vender-mas-sin-sumar-personal/) | 18/05/2026 | T2 | Sustituto gratuito de Meta; Argentina primer país |
| 8 | [iProfesional — topes de monotributo septiembre 2026](https://www.iprofesional.com/impuestos/463297-arca-definio-el-monotributo-cuanto-se-paga-en-septiembre-2026-y-cuales-son-nuevos-topes.amp) | sep-2026 | T2 | Tope de K ≈ $126,6 M/año |
| 9 | [BCRA — Informe de Pagos Minoristas](https://www.bcra.gob.ar/publicaciones/informe-de-pagos-minoristas-2025/) | 2025 | T1 | QR/PCT +40,7% interanual |
| 10 | [Base.com — Digitalización ferretera](https://base.com/es-AR/blog/digitalizacion-ferretera-como-automatizar-catalogos-masivos/) | 2026 | T3 | 3.000–30.000 SKU en ferreterías online; consultas técnicas repetitivas |
| 11 | [Servidos.ar — Distribuidores de plomería en Buenos Aires](https://servidos.ar/donde-comprar/plomeria) | 2026 | T3 | Sanitarios Hidro (Liniers) abastece a ferreterías y corralones |
| 12 | [Tiendanube — Dux Software ERP](https://ayuda.tiendanube.com/es_AR/139131-aplicaciones-de-gestion-y-facturacion/como-integrar-dux-software-con-mi-tienda) · [GetApp — Líder Gestión](https://www.getapp.sg/software/2080119/lider-gestion) | 2026 | T3 | Capacidades de los sistemas de gestión |
| 13 | [Bumeran — Vendedor viajante para distribuidora mayorista de ferretería](https://www.bumeran.com.ar/empleos/vendedor-viajante-para-distribuidora-mayorista-de-ferreteria-cocina-consultoria-de-empresas-familiares-1118418210.html) | 2026 | T3 | Existencia de viajantes de mayoristas |
| 14 | [Mercado.com.ar — IA en pymes argentinas (nadIA, Di Tella/Fundar)](https://mercado.com.ar/ruta-digital/ia-en-pymes-argentinas-416-ya-la-usa-pero-57-no-mide-impacto) | 2026 | T2 | 41,6% de pymes (10–249 empleados) usa IA |
