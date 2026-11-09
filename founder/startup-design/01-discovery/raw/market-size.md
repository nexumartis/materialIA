# Tamaño de mercado y economía: materialIA

> **Insumo original de investigación, 09/11/2026.** Se conserva como antecedente, sin certificar sus afirmaciones. Para decisiones usar las síntesis y [correcciones posteriores](../corrections-2026-11-09.md); las tarifas de servicio de Meta y sus escenarios derivados quedaron retirados.

Agente A1 (Market Sizing & Economics). Fecha: 09/11/2026. Precio analizado: **ARS 70.000/mes fijo** (antes de IVA).

Etiquetas: **[Data]** dato publicado · **[Estimate]** cuenta propia sobre datos · **[Assumption]** supuesto sin dato · **[Opinion]** juicio. Tiers: T1 (oficial, cámara, consultora), T2 (prensa seria, comunicado), T3 (blog o vendedor). **VIEJO** = más de 18 meses (antes de mayo de 2025).

> Aviso: `cfo.md` usa **$35.000/mes** y **USD 1 = ARS 1.450**. Este informe usa **$70.000** y el MEP del **06/11/2026, $1.578,78**. A ese tipo de cambio la IA estimada (USD 10) cuesta **$15.788** por comercio, no $14.500. Hay que actualizar la planilla del CFO.

---

## Resumen de 30 segundos

| Número | Valor | Etiqueta | Confianza |
|---|---|---|---|
| Ferreterías en Argentina | ~15.000 | [Data] CAFARA, T2, 2023, VIEJO | Media |
| Puntos de venta del canal (ferreterías + sanitarios + derivados) | >25.000 | [Data] ExpoFerretera/CAFARA, T2, 2017, VIEJO | Baja-media |
| TAM Argentina a $70.000 | ARS 12.600–21.000 M/año (USD 8,0–13,3 M) | [Estimate] | Baja-media |
| SAM AMBA | ~2.100 comercios, ARS 1.790 M/año (USD 1,1 M) | [Estimate] con 2 supuestos fuertes | Baja |
| SOM a 12 meses | 30–40 comercios, ARS 25–34 M/año de run-rate | [Estimate] | Media (depende de ventas) |
| ARS 70.000 en dólares | USD 44,3 (MEP) | [Data] Ámbito, 06/11/2026 | Alta |
| Churn mensual de referencia, SaaS para pymes | 3–7% | [Data] blogs y vendedores, T3, no es del segmento | Baja |

---

## TAM: todos los comercios del rubro en Argentina

### Datos de base

| Dato | Valor | Fuente | Fecha | Tier | Etiqueta |
|---|---|---|---|---|---|
| Ferreterías en el país | ~15.000, «se estima», sin registro oficial | CAFARA (pres. Sergio Angiulli), vía [Diario Jornada](https://www.diariojornada.com.ar/353795/magazine/dia_de_los_ferreteros_el_cosito_del_coso_y_me_muestra_la_lija_otras_galimatias_de_un_oficio_centenario) | 02/09/2023 | T2 (cita a la cámara) | [Data] VIEJO |
| Empresas del sector ferretero | ~14.000: 90% ferreterías barriales, ~10% industriales, mayoristas 1%; 34.000 empleados | [Gacetilla ExpoFerretera 2019](https://ar.messefrankfurt.com/content/dam/messefrankfurt-argentina/corpotativa-mfa/press-releases/2019/13_EF2019_SEP2019_Reporte_Final_ES.pdf) (Messe Frankfurt + CAFARA) | 09/2019 | T2 | [Data] VIEJO |
| Canal ferretero completo | 1.300 fábricas, 80 importadores, **600 distribuidores mayoristas**, **>25.000 puntos de venta** («comercios, ferreterías y derivados»), 50.000 empleos | [Reporte final ExpoFerretera 2017](https://expoferretera.ar.messefrankfurt.com/content/dam/messefrankfurt-argentina/expoferretera/press-releases/2017/14_EF2017_SEP2017_ReporteFinal_ES.pdf) | 09/2017 | T2 | [Data] VIEJO |
| Comercios del rubro | «más de 5 mil» | [Diario Uno](https://www.diariouno.com.ar/cuarentena/ferreterias-incrementaron-20-las-ventas-n575856) | 2020 | T2 | [Data] VIEJO, valor atípico |
| Socios de CAFARA | ~300, mayoría pymes familiares | [BAE Negocios](https://www.baenegocios.com/amp/Duenos-de-ferreterias-piden-que-se-baje-el-IVA-a-productos-de-primera-necesidad-20231031-0073/) | 31/10/2023 | T2 | [Data] VIEJO |
| Distribuidores activos de FV (grifería) | 2.000 (sin aclarar si son todos de Argentina) | [Ficha FV en ARQA](https://arqa.com/empresas/fichas/fv-s-a) | sin fecha | T3 | [Data] proxy |
| Concentración geográfica | La mayor parte de los puntos de venta está en el centro del país (AMBA, PBA, Córdoba, Santa Fe) | Gacetilla ExpoFerretera 2019 | 2019 | T2 | [Data] VIEJO, cualitativo |

**Cruce.** Tres fuentes ligadas a CAFARA dan 14.000 (2019), 15.000 (2023) y más de 25.000 puntos de venta (2017). Son consistentes si los 25.000 suman sanitarios, pinturerías y otros derivados. Diario Uno dice «más de 5 mil» y no coincide con ninguna. **Le creo a 15.000 ferreterías y a ~25.000 como techo del canal ampliado** [Opinion]: las tres cifras de la cámara coinciden y la de Diario Uno no aclara el criterio. Ojo: todas son estimaciones de la cámara (que no tiene registro oficial, según ella misma) y todas son VIEJAS.

**Mayoristas: no coinciden.** El dato de 2017 dice 600 distribuidores mayoristas. El de 2019, «1% de 14.000», da unos 140. Le creo más a **140–600 como rango** [Opinion]: el 600 parece contar distribuidores de todas las líneas y el 1% parece contar sólo mayoristas de ferretería.

**Casas de sanitarios y corralones: no hay conteo.** Ver Data gaps.

### Cuenta del TAM [Estimate]

TAM = comercios × precio × 12

- Alto: 25.000 × $70.000 × 12 = **ARS 21.000 M/año** → al MEP $1.578,78 = **USD 13,3 M/año**
- Bajo (sólo ferreterías): 15.000 × $70.000 × 12 = **ARS 12.600 M/año** → **USD 8,0 M/año**

[Opinion] Es un TAM chico. Alcanza para un negocio rentable de dos personas, no para una historia de capital de riesgo, salvo que se sumen otros rubros u otros países.

### Facturación del sector

- «Movimiento anual aproximado de $15.000 millones» en 2017 (ExpoFerretera 2017, T2) [Data] VIEJO. Esos pesos de 2017 no sirven hoy.
- Mercado de loza sanitaria de Argentina: **USD 77,2 M en 2025**, con proyección de USD 130,2 M a 2034 (CAGR 5,8%) ([IMARC](https://www.imarcgroup.com/argentina-sanitary-ware-market), actualizado el 08/07/2026) [Data], T1 en el papel. [Opinion] Le tengo poca confianza: IMARC hace informes en serie, con poco trabajo de campo local, y la cifra parece sólo de artefactos, sin grifería ni ferretería.
- Ventas de ferretería, materiales eléctricos y de construcción (CAME): **+0,3% interanual en agosto de 2026, +0,3% acumulado en el año**, −0,2% contra julio ([BAE Negocios](https://www.baenegocios.com/economia/las-ventas-minoristas-volvieron-a-caer-en-agosto-y-acumulan-una-baja-del-2-4-en-2026-2172/), 06/09/2026, T2 que cita a T1) [Data]. El rubro está estancado, no en caída.
- **DATA GAP:** facturación actual del sector en pesos.

---

## SAM: lo que se puede atender con el producto y el plan de hoy

Filtros: (1) minorista en AMBA, primero CABA; (2) vende o atiende por WhatsApp; (3) tiene o puede armar una lista de precios y stock en planilla, cobra con Mercado Pago y factura (paga una suscripción formal).

### Paso 1: geografía [Estimate]

No hay conteo por zona, así que uso la población como proxy [Assumption]: la cantidad de comercios sigue a la población.

- Censo 2022 ([INDEC vía C5N](https://www.c5n.com/sociedad/argentina-tiene-45892285-habitantes-el-indec-dio-conocer-los-datos-definitivos-del-censo-2022-n135804); [IEC CABA](https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/03/La_Ciudad_Buenos_Aires_entre_Censos_2010_2022_Caracteristicas_demograficas.pdf)): país 45.892.285; CABA 3.121.707; 24 partidos del GBA 10.865.182 (cifra provisoria) [Data] T1.
- CABA = 6,8% del país. AMBA (CABA + 24 partidos) = 30,5%.
- CABA: 25.000 × 6,8% = **~1.700** (1.020 si se toman 15.000).
- AMBA: 25.000 × 30,5% = **~7.620** (4.570 si se toman 15.000).

[Opinion] Probablemente subestima AMBA, porque ExpoFerretera dice que los puntos de venta se concentran en el centro del país. También puede sobreestimar CABA, donde los locales son menos y más grandes que en el conurbano.

### Paso 2: venden por WhatsApp

- **71,5%** de los emprendedores argentinos usó WhatsApp como canal de venta en 2025 (NubeCommerce 2026, citado en el [blog de Tiendanube](https://www.tiendanube.com/blog/como-vender-por-whatsapp/), actualizado el 20/07/2026) [Data] T2/T3, con sesgo: son tiendas online, no ferreterías de barrio. No publica muestra.
- **62%** de los usuarios argentinos compró un producto por WhatsApp y **66%** contrató un servicio (Infobip, *Messaging Trends Report 2026*, vía [Mercado](https://mercado.com.ar/tendencias/el-informe-de-infobip-describe-a-whatsapp-como-infraestructura-social-en-argentina), 04/09/2026) [Data] T2. La nota no atribuye con claridad la fuente de estos porcentajes, y Infobip vende mensajería.
- 50% de los emprendedores encuestados por CAME Joven vendía online (280 casos, [CAME](https://www.redcame.org.ar/advf/documentos/2021/03/605cf2aa21824.%20segunda%20encuesta.%20came%20joven.pdf), 2021) [Data] VIEJO, no separa WhatsApp.
- Las ventas online de comercios con local a la calle subieron 17,6% interanual en agosto de 2026 (CAME, vía BAE) [Data] T2.

Supuesto: **70%** de las ferreterías o casas de sanitarios del AMBA atiende consultas de venta por WhatsApp [Assumption]. Es parecido al 71,5% de Tiendanube; [Opinion] en una ferretería de barrio podría ser más (el WhatsApp del local es universal) o menos (si sólo se usa para avisos).

### Paso 3: «digitalizable y paga suscripción formal»

Supuesto: **40%** tiene la lista de precios en Excel o Sheets (o la puede armar), cobra con Mercado Pago o transferencia y acepta una suscripción facturada [Assumption]. **Es el supuesto más débil de todo el informe.** No encontré ningún dato. Ver Data gaps.

### Cuenta del SAM [Estimate]

| | Comercios | ARS/año a $70.000 | USD/año (MEP) |
|---|---|---|---|
| **SAM AMBA** = 7.620 × 0,70 × 0,40 | **~2.130** | **ARS 1.792 M** | **USD 1,14 M** |
| SAM AMBA, versión baja (base 15.000) | ~1.280 | ARS 1.075 M | USD 0,68 M |
| **SAM CABA** = 1.700 × 0,70 × 0,40 | **~475** | ARS 400 M | USD 0,25 M |
| SAM CABA, versión baja | ~285 | ARS 240 M | USD 0,15 M |

Los mayoristas y distribuidores (140–600 en todo el país) quedan fuera del SAM de hoy. Son la etapa 2 y probablemente pagarían más que $70.000 [Opinion].

---

## SOM: lo que dos founders sin inversión pueden capturar

Restricciones reales: dos estudiantes, USD 100/mes, instalación hecha por los socios (reunión virtual o presencial), venta fundada en el contacto directo.

### Capacidad de venta e instalación [Assumption]

- Altas posibles: **3–5 comercios por mes** (venta cara a cara en CABA más una instalación de 1–3 h por cada alta, con dos personas a tiempo parcial).
- Churn mensual: **4%** de base, **6%** pesimista (ver Benchmarks).

### Cuenta: activos al mes 12, con 4 altas por mes [Estimate]

N(12) = altas × (1 − (1 − churn)^12) / churn

- Churn 4%: 4 × (1 − 0,96^12) / 0,04 = **~39 comercios**
- Churn 6%: 4 × (1 − 0,94^12) / 0,06 = **~35 comercios**

Coincide con el plan de `cfo.md` (40 al mes 12). Esos ~39 son el **1,8% del SAM AMBA** y el **8% del SAM CABA**.

| Horizonte | Comercios | Run-rate anual a $70.000 | USD (MEP) |
|---|---|---|---|
| SOM 12 meses | 30–40 | ARS 25–34 M | USD 16.000–21.300 |
| SOM 36 meses (AMBA, 5–7% del SAM) | 100–150 | ARS 84–126 M | USD 53.000–80.000 |

[Opinion] El techo no es el mercado, es la capacidad de vender e instalar. Con 4% de churn y 4 altas por mes, la base se estabiliza en unos 100 comercios (altas ÷ churn). Para pasar de ahí hacen falta autoinstalación o un canal (distribuidores como FV, cámaras como CAFARA).

---

## Benchmarks de economía unitaria

### Contribución por comercio a $70.000 [Estimate]

Costos de `cfo.md` actualizados al MEP:

| Línea | ARS/mes |
|---|---|
| Precio | 70.000 |
| IA (USD 10 estimado × 1.578,78) | −15.788 |
| Comisión de cobro (7,6%, dato de `cfo.md`, sin confirmar) | −5.320 |
| **Contribución** | **48.892 (69,8%)** |

### Churn

| Fuente | Dato | Segmento | Tier | Comentario |
|---|---|---|---|---|
| [Recurly](https://www.recurly.com/research/churn-rate-benchmarks/) (datos a julio de 2026) | B2B 3,44%, B2B software 3,22% (la página también dice 3,21% y 3,04%) | General, global | T1/T3 (vendedor con datos propios) | La página **no deja claro si es mensual o anual** y se contradice. Otros sitios lo citan como mensual. No lo usaría solo. |
| Vena, Ecosistema Startup, otros blogs ([resumen](https://ecosistemastartup.com/?p=59797)) | SMB 3–5% mensual («saludable»), alerta >7%; Vena: 3–7% mensual (30–58% anual) | SaaS para pymes, global | T3 | Rango repetido en varias fuentes, pero ninguna primaria |
| Riverwood Capital, *LatAm SaaS Survey 2025* (vía [LatAm Tech Weekly](https://juliadeluca.substack.com/p/latam-tech-weekly-ff4), 14/12/2025) | NRR mediano: ~96% en SaaS para pymes, ~107% en enterprise; ~150 empresas | **LatAm**, SaaS para pymes | T1 vía T3 | No publica churn. NRR < 100% indica que las pymes de LatAm pierden más ingreso del que se expande. |
| Caso Vendedor.io (Chile) | 3,5% mensual | Pymes, LatAm | T3, sin fuente primaria | Anecdótico |
| SaaS de inventario en Argentina | de 4% a 9% mensual en la crisis 2020–21 | Pymes, Argentina | T3, sin fuente | Anecdótico, pero muestra que el churn sube con las crisis |

**Usar 4% mensual de base y 6% pesimista** [Opinion]. El 3–5% se repite para pymes en general. Un comercio chico argentino, en un rubro estancado y con mora en alza, debería estar en la mitad alta o arriba. **No hay ningún dato del segmento** (comercios de ferretería o sanitarios).

**Inflación como churn oculto:** con el precio fijo en pesos, el IPC de 1,9% mensual (septiembre de 2026) le saca valor real al ingreso todos los meses. El precio tiene que actualizarse con un índice: Tiendanube lo actualiza cada trimestre ([ayuda Tiendanube](https://ayuda.tiendanube.com/es_ES/123482-planes/como-se-ajusta-el-precio-de-los-planes-de-tiendanube)).

### LTV [Estimate]

LTV = contribución / churn mensual

| Churn | LTV (ARS) | USD (MEP) |
|---|---|---|
| 3% | 1.629.740 | 1.032 |
| 4% (base) | 1.222.305 | 774 |
| 6% | 814.870 | 516 |
| 4% + 1,9% de erosión por inflación (precio sin indexar) | 828.681 | 525 |

### CAC

- **DATA GAP:** no hay CAC publicado para SaaS de pymes en Argentina.
- Referencias generales: LTV:CAC ≥ 3:1 y repago del CAC en menos de 12–18 meses ([Rework](https://resources.rework.com/es/libraries/pipeline-management/ltv-cac-ratio), T3, origen David Skok). Riverwood dice que el repago en LatAm está «en línea con las buenas prácticas globales», sin dar cifras (T3).
- **CAC máximo tolerable** [Estimate]: LTV $1.222.305 / 3 = **~ARS 407.000 por comercio** (unas 8 cuotas). Hoy el CAC en efectivo es casi cero porque venden los founders, pero el CAC en horas es real. [Opinion] Si cada alta lleva 6–10 h (visita, demo, carga de la planilla, alta de WhatsApp en Meta), ese es el costo verdadero.

### Ticket y disposición a pagar

| Referencia | Precio | Moneda | Fuente | Fecha | Tier |
|---|---|---|---|---|---|
| Tiendanube Esencial | $27.999/mes ($20.999 con pago anual) | ARS | [tiendanube.com/planes-y-precios](https://www.tiendanube.com/planes-y-precios?c=AR) | vista el 09/11/2026 | T1 (precio público) |
| Tiendanube Impulso | $79.999/mes ($59.999 con pago anual) | ARS | idem | idem | T1 |
| Tiendanube Escala | $244.999/mes | ARS | idem | idem | T1 |
| Competidores con IA por chat | USD 35–300/mes (mediana USD 149) | USD | `competitors.md` | 05/11/2026 | — |
| **materialIA** | **$70.000 = USD 44,3** | ARS | — | — | — |

[Opinion] $70.000 queda entre Esencial e Impulso de Tiendanube, la referencia en pesos más parecida que conoce un comercio chico. Es un tercio de la mediana en dólares de los competidores (USD 149). El precio parece defendible; falta que alguien lo pague.

**Pesos vs. dólares:** sólo Tiendanube y Chat Nube cobran en pesos; los SaaS de chat cobran en dólares (`competitors.md`). La brecha MEP/oficial es de 2,2% (Ámbito, 06/11/2026), así que hoy cobrar en dólares no es un problema cambiario. [Opinion] Para el dueño de una ferretería, un precio fijo en pesos es más fácil de aceptar. **DATA GAP:** no hay encuesta de disposición a pagar en pesos o en dólares en este segmento.

### Gasto en software de pymes argentinas

- **41,6%** de las pymes de 10 a 249 empleados usa al menos una herramienta de IA. De esas, 78,3% no tiene una partida específica y sólo **7,5%** tiene presupuesto propio para IA (encuesta nadIA, CEPE-Di Tella + Fundar, 402 pymes, vía [Perfil](https://www.perfil.com/noticias/economia/cuatro-de-cada-diez-pymes-argentinas-ya-usan-ia-pero-pocas-miden-su-impacto-a40.phtml) e [iProfesional](https://www.iprofesional.com/tecnologia/467797-la-baja-inversion-y-la-escasa-adopcion-frenan-la-ia-en-argentina)) [Data] T1 vía T2. Ojo: son pymes de 10+ empleados; la ferretería de barrio suele tener menos.
- **DATA GAP:** cuánto gasta por mes en software una ferretería o casa de sanitarios.

---

## Tipo de cambio

Último cierre hábil disponible: **viernes 06/11/2026**.

| Cotización | Valor | Fuente | Tier |
|---|---|---|---|
| Oficial BNA | compra $1.520 / **venta $1.570** | [Ámbito](https://www.ambito.com/finanzas/dolar-hoy-cuanto-cerro-este-viernes-6-noviembre-n6342535) | T2 |
| Mayorista | $1.545,50 | Ámbito | T2 |
| **MEP** | **$1.578,78** | Ámbito | T2 |
| MEP (cruce) | $1.576,90 venta | [El Cronista](https://www.cronista.com/finanzas-mercados/dolar-blue-hoy-a-cuanto-cotiza-el-viernes-6-de-noviembre-con-el-mep-y-el-ccl/) | T2 |
| MEP (cruce) | $1.580,17 venta | [El Litoral](https://www.ellitoral.com/economia/cerro-dolar-bancos-argentinos-viernes-6-noviembre-2026-blue-mep_0_Vg5MT4l5Sx.html) | T2 |
| MEP AL30 (cruce) | $1.583,82 | [Río Negro](https://www.rionegro.com.ar/economia/dolar-oficial-a-cuanto-cerro-en-el-banco-nacion-este-viernes-6-de-noviembre-2026-y-que-marca-el-feriado-bancario-4787988/) | T2 |
| CCL | $1.678,72 | Ámbito | T2 |
| Blue | $1.535 / $1.555 | Ámbito | T2 |

Las fuentes coinciden: MEP entre $1.576 y $1.588 según el bono y la hora. **Uso $1.578,78 (Ámbito)** porque es el cierre del día y trae todas las cotizaciones juntas. No consulté el BCRA ni BYMA directamente.

Conversiones: $70.000 = USD 44,3 al MEP = USD 44,6 al oficial BNA.

**Inflación** (contexto para indexar): IPC de septiembre de 2026 **1,9% mensual, 23,6% acumulado en el año, 33,4% interanual**; agosto, 1,7% ([Canal 26](https://www.canal26.com/economia/2026/10/13/la-inflacion-de-septiembre-fue-de-19-y-acumula-un-alza-de-236-en-lo-que-va-del-2026/), [Diario Panorama](https://diariopanorama.com/noticia/569591/indec-confirmo-inflacion-septiembre-fue-19porciento-acumula-334porciento-doce-meses), 13/10/2026) [Data] T2 que cita a INDEC. El IPC de octubre sale el 12/11/2026.

---

## Obstáculos del mercado (chequeo de realidad)

1. **Rubro estancado.** CAME: ferretería +0,3% interanual en agosto de 2026; las ventas minoristas pyme acumulan −2,4% en el año (BAE, 06/09/2026, T2). Otras notas cuentan 13 meses seguidos de caída del índice general hasta mediados de 2026 ([La Voz de San Justo](https://www.lavozdesanjusto.com.ar/las-ventas-minoristas-de-pymes-cayeron-56-interanual-en-febrero-y-acumulan-diez-meses-en-baja), T2) [Data]. Un dueño con ventas planas recorta gastos fijos antes de sumar uno nuevo [Opinion].
2. **Mora pyme en alta.** En enero de 2026, la cartera pyme con atrasos de más de 90 días llegó al **8,2%** y la mora pyme subió 93,5% en un año ([iProfesional](https://www.iprofesional.com/economia/452752-morosidad-entre-pymes-se-disparo-y-el-bcra-busca-evitar-quiebras-masivas), [La Gaceta](https://www.lagaceta.com.ar/nota/1133460/economia/morosidad-entre-pymse-dispara-bcra-busca-evitar-ola-quiebras.html), T2 que citan al BCRA). Según Banco Provincia, 1 de cada 8 empresas tenía atrasos. La irregularidad del total de empresas fue 3,6% en julio de 2026 ([Misiones Online](https://misionesonline.net/2026/09/18/mora-en-el-pais-en-julio/), T2) [Data]. Las cifras no coinciden porque miden distinto (por cantidad o por monto, sólo pymes o todas las empresas), pero todas suben. **Consecuencia:** cobrar por adelantado o por débito automático con Mercado Pago, nunca a mes vencido.
3. **Inflación de ~2% mensual.** Un precio fijo pierde ~21% real en un año. Hay que pactar una indexación trimestral desde el día uno.
4. **Informalidad.** No encontré el dato del rubro (DATA GAP). [Opinion] Una parte de las ventas de ferretería de barrio se hace en efectivo y sin factura. Un agente que cobra con Mercado Pago deja rastro, y algunos dueños pueden resistirse por eso. Además, el dueño necesita una factura nuestra para descontar el gasto.
5. **Catálogo sucio.** Una ferretería maneja miles de artículos con precios que cambian por listas de proveedor. Los competidores dicen que el bot «se equivoca» (`competitors.md`). [Opinion] El costo de mantener la planilla al día lo paga el dueño. Si no la actualiza, el agente cotiza mal y el cliente se va. Es el principal riesgo de churn propio.
6. **Rotación y cierre de comercios.** Hay datos de cierre de pymes en 2026 (16.500 «en lo que va del año», según el Frente Productivo Nacional vía [El Economista](https://eleconomista.com.ar/economia/confirmado-ya-cerraron-16500-pymes-lo-va-ano-cae-consumo-que-dicen-empresarios-n79303/amp)), pero la fuente es gremial, la fecha no está clara y no hay dato del rubro [Data] T2, confianza baja. Los 90.700 locales cerrados que informó CAME son de 2020, no de hoy.
7. **Meta y Tiendanube.** Ver `competitors.md`. Si el agente gratis de Meta suma carrito y cobro, el precio de referencia cae a centavos.

---

## Evaluación de fuentes

| Fuente | Tier | Para qué la usé | Confianza | Por qué |
|---|---|---|---|---|
| Gacetillas ExpoFerretera 2017/2019 (Messe Frankfurt + CAFARA) | T2 | Cantidad de comercios y mayoristas | Media-baja | Las leí en el PDF original, pero son números redondos de cámara sin metodología, y tienen 7–9 años |
| CAFARA vía Diario Jornada (2023) | T2 | 15.000 ferreterías | Media | Coincide con 2019; la propia cámara dice que no hay registro oficial |
| INDEC, Censo 2022 | T1 | Proxy geográfico | Alta en el dato, baja como proxy | Que los comercios sigan a la población es un supuesto |
| Ámbito / Cronista / El Litoral (dólar) | T2 | Tipo de cambio | Alta | Tres fuentes dentro de un 0,2% |
| NubeCommerce 2026 (Tiendanube) | T2/T3 | % que vende por WhatsApp | Media-baja | Empresa interesada, muestra de tiendas online, sin metodología publicada |
| Infobip *Messaging Trends 2026* | T2/T3 | Compras por WhatsApp | Baja-media | Vendedor de mensajería; la nota no atribuye bien la fuente de los porcentajes |
| CAME (vía BAE) | T1 vía T2 | Ventas del rubro | Media-alta | Serie mensual consistente; no leí el PDF original |
| nadIA (Di Tella + Fundar) | T1 vía T2 | Adopción de IA en pymes | Media | Metodología seria, pero en pymes de 10+ empleados |
| Recurly | T1/T3 | Churn | Baja | La página se contradice y no aclara si es mensual o anual |
| Riverwood vía newsletter | T1 vía T3 | NRR de SaaS para pymes en LatAm | Media-baja | No pude leer el informe original |
| IMARC | T1 (en teoría) | Mercado de sanitarios | Baja | Informe en serie, alcance dudoso |
| Blogs de churn y CAC (Ecosistema Startup, Vena, Rework) | T3 | Rangos de referencia | Baja | Sin fuentes primarias, pero el rango 3–7% se repite |
| Tiendanube, precios públicos | T1 | Ancla de precio en pesos | Alta | Precio publicado, visto hoy |

---

## Data gaps

1. **DATA GAP: cantidad oficial de comercios por actividad (CLAE) en CABA y AMBA.** Existe el dataset oficial *Distribución geográfica de los establecimientos productivos* (CEP XXI, AFIP/SIPA, última actualización 06/12/2023) en [datos.produccion.gob.ar](https://datos.produccion.gob.ar/dataset/distribucion-geografica-de-los-establecimientos-productivos), con conteos por departamento y por código CLAE6. **No lo pude bajar: el certificado HTTPS de cdn.produccion.gob.ar está vencido**, y salteé la verificación por seguridad. **Cómo llenarlo:** bajar a mano `Datos_por_departamento_y_actividad.csv` desde el navegador y filtrar estos CLAE: **475230** (ferretería y materiales eléctricos), **475250** (plomería e instalación de gas), **475260** (cristales, espejos y mamparas, a confirmar en el diccionario), **475290** (materiales de construcción n.c.p., corralones) y los mayoristas **4663xx** (incluye 466360, plomería, gas y calefacción). Sacar CABA (comunas) y los 24 partidos. Ojo: sólo cuenta establecimientos con empleados registrados; deja afuera a los unipersonales. Con eso el SAM pasa de supuesto a dato.
2. **DATA GAP: casas de sanitarios y corralones.** Busqué con tres formulaciones (cámara del sector sanitario, «corralones en todo el país», Construya/CUANOBA) y no apareció ningún conteo. El único proxy son los 2.000 distribuidores de FV (sin fecha ni país). **Cómo llenarlo:** el CSV del punto 1 (CLAE 475250 y 475290), o preguntarle a CUANOBA (corralones del oeste bonaerense) y a los departamentos comerciales de FV o Ferrum cuántos clientes activos tienen en AMBA.
3. **DATA GAP: % de ferreterías que tienen el stock en planilla y cobran con Mercado Pago.** Es el supuesto del 40% y mueve todo el SAM. **Cómo llenarlo:** recorrer 30–50 locales en CABA (2–3 barrios) con 5 preguntas: ¿Vendés por WhatsApp? ¿Cuántos mensajes por día? ¿Tenés los precios en Excel o en un sistema? ¿Cobrás con Mercado Pago? ¿Pagás algún software por mes y cuánto?
4. **DATA GAP: volumen de consultas por WhatsApp de una ferretería** (mensajes por día y conversaciones por mes). No hay ningún dato público. Define el costo de IA (USD 10 estimado). **Cómo llenarlo:** la misma encuesta, más medirlo en el piloto.
5. **DATA GAP: churn, CAC y disposición a pagar en el segmento.** Ningún benchmark es de comercios de ferretería o sanitarios de Argentina. **Cómo llenarlo:** sólo con clientes reales; registrar desde el cliente 1 las altas, las bajas y su motivo, y las horas de venta e instalación por alta.
6. **DATA GAP: informalidad del rubro y facturación actual del sector en pesos.** **Cómo llenarlo:** pedírselo a CAFARA (cafara.org.ar) o consultar el Índice Construya y las publicaciones de la Cámara Argentina de la Construcción.
7. **DATA GAP: IPC de octubre de 2026** (sale el 12/11/2026) y la cifra definitiva de los 24 partidos en el Censo 2022 (usé la provisoria).

---

## Fuentes

- Diario Jornada, «Día de los Ferreteros…», 02/09/2023: https://www.diariojornada.com.ar/353795/magazine/dia_de_los_ferreteros_el_cosito_del_coso_y_me_muestra_la_lija_otras_galimatias_de_un_oficio_centenario
- Messe Frankfurt / CAFARA, gacetilla ExpoFerretera 2019: https://ar.messefrankfurt.com/content/dam/messefrankfurt-argentina/corpotativa-mfa/press-releases/2019/13_EF2019_SEP2019_Reporte_Final_ES.pdf
- Messe Frankfurt / CAFARA, reporte final ExpoFerretera 2017: https://expoferretera.ar.messefrankfurt.com/content/dam/messefrankfurt-argentina/expoferretera/press-releases/2017/14_EF2017_SEP2017_ReporteFinal_ES.pdf
- BAE Negocios, CAFARA con 300 socios, 31/10/2023: https://www.baenegocios.com/amp/Duenos-de-ferreterias-piden-que-se-baje-el-IVA-a-productos-de-primera-necesidad-20231031-0073/
- Diario Uno, ferreterías en la cuarentena, 2020: https://www.diariouno.com.ar/cuarentena/ferreterias-incrementaron-20-las-ventas-n575856
- ARQA, ficha de FV: https://arqa.com/empresas/fichas/fv-s-a
- IMARC, Argentina Sanitary Ware Market (08/07/2026): https://www.imarcgroup.com/argentina-sanitary-ware-market
- El Cronista, Disensa abrirá 1.000 locales, 26/04/2021: https://www.cronista.com/negocios/tiemblan-los-corralones-una-cementera-abrira-1000-locales-de-venta-de-materiales-en-tres-anos
- CEP XXI, Distribución geográfica de los establecimientos productivos: https://datos.produccion.gob.ar/dataset/distribucion-geografica-de-los-establecimientos-productivos
- C5N / INDEC, Censo 2022 definitivo: https://www.c5n.com/sociedad/argentina-tiene-45892285-habitantes-el-indec-dio-conocer-los-datos-definitivos-del-censo-2022-n135804
- IEC CABA, La Ciudad entre censos 2010–2022: https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/03/La_Ciudad_Buenos_Aires_entre_Censos_2010_2022_Caracteristicas_demograficas.pdf
- Tiendanube, «Cómo vender por WhatsApp» (NubeCommerce 2026), 20/07/2026: https://www.tiendanube.com/blog/como-vender-por-whatsapp/
- Mercado, informe de Infobip, 04/09/2026: https://mercado.com.ar/tendencias/el-informe-de-infobip-describe-a-whatsapp-como-infraestructura-social-en-argentina
- CAME Joven, segunda encuesta, 2021: https://www.redcame.org.ar/advf/documentos/2021/03/605cf2aa21824.%20segunda%20encuesta.%20came%20joven.pdf
- BAE Negocios, ventas minoristas de agosto de 2026, 06/09/2026: https://www.baenegocios.com/economia/las-ventas-minoristas-volvieron-a-caer-en-agosto-y-acumulan-una-baja-del-2-4-en-2026-2172/
- La Voz de San Justo, ventas minoristas pyme de febrero de 2026: https://www.lavozdesanjusto.com.ar/las-ventas-minoristas-de-pymes-cayeron-56-interanual-en-febrero-y-acumulan-diez-meses-en-baja
- Perfil, encuesta nadIA: https://www.perfil.com/noticias/economia/cuatro-de-cada-diez-pymes-argentinas-ya-usan-ia-pero-pocas-miden-su-impacto-a40.phtml
- iProfesional, IA en Argentina: https://www.iprofesional.com/tecnologia/467797-la-baja-inversion-y-la-escasa-adopcion-frenan-la-ia-en-argentina
- Tiendanube, planes y precios (vista el 09/11/2026): https://www.tiendanube.com/planes-y-precios?c=AR
- Tiendanube, ajuste de precios de los planes: https://ayuda.tiendanube.com/es_ES/123482-planes/como-se-ajusta-el-precio-de-los-planes-de-tiendanube
- Recurly, Churn Rate Benchmarks: https://www.recurly.com/research/churn-rate-benchmarks/
- LatAm Tech Weekly (Riverwood LatAm SaaS Survey 2025), 14/12/2025: https://juliadeluca.substack.com/p/latam-tech-weekly-ff4
- Ecosistema Startup, Churn Rate: https://ecosistemastartup.com/?p=59797
- Rework, ratio LTV:CAC: https://resources.rework.com/es/libraries/pipeline-management/ltv-cac-ratio
- Ámbito, cierre del dólar del 06/11/2026: https://www.ambito.com/finanzas/dolar-hoy-cuanto-cerro-este-viernes-6-noviembre-n6342535
- El Cronista, dólar del 06/11/2026: https://www.cronista.com/finanzas-mercados/dolar-blue-hoy-a-cuanto-cotiza-el-viernes-6-de-noviembre-con-el-mep-y-el-ccl/
- El Litoral, dólar del 06/11/2026: https://www.ellitoral.com/economia/cerro-dolar-bancos-argentinos-viernes-6-noviembre-2026-blue-mep_0_Vg5MT4l5Sx.html
- Río Negro, dólar del 06/11/2026: https://www.rionegro.com.ar/economia/dolar-oficial-a-cuanto-cerro-en-el-banco-nacion-este-viernes-6-de-noviembre-2026-y-que-marca-el-feriado-bancario-4787988/
- Canal 26, IPC de septiembre de 2026, 13/10/2026: https://www.canal26.com/economia/2026/10/13/la-inflacion-de-septiembre-fue-de-19-y-acumula-un-alza-de-236-en-lo-que-va-del-2026/
- Diario Panorama, IPC de septiembre de 2026: https://diariopanorama.com/noticia/569591/indec-confirmo-inflacion-septiembre-fue-19porciento-acumula-334porciento-doce-meses
- iProfesional, mora pyme: https://www.iprofesional.com/economia/452752-morosidad-entre-pymes-se-disparo-y-el-bcra-busca-evitar-quiebras-masivas
- La Gaceta, mora pyme: https://www.lagaceta.com.ar/nota/1133460/economia/morosidad-entre-pymse-dispara-bcra-busca-evitar-ola-quiebras.html
- Misiones Online, mora de julio de 2026: https://misionesonline.net/2026/09/18/mora-en-el-pais-en-julio/
- El Economista, 16.500 pymes cerradas: https://eleconomista.com.ar/economia/confirmado-ya-cerraron-16500-pymes-lo-va-ano-cae-consumo-que-dicen-empresarios-n79303/amp
