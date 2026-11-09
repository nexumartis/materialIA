# Análisis de mercado

> **Actualización del 09/11/2026:** leer [correcciones y límites](corrections-2026-11-09.md) junto con este documento. La investigación es insumo para validar; no acredita entrevistas, precios aceptados ni un piloto real.

**Phase:** 3 — Investigación de mercado (síntesis)
**Project:** materialia
**Date:** 2026-11-09
**Confidence:** Media (conteo de CABA: alta; resto del país y supuestos de digitalización: baja)

---

## Resumen ejecutivo
1. El mercado es **chico y concreto**: en CABA hay **390 casas de sanitarios y plomería y 1.181 ferreterías** censadas [Data, GCBA RUS 2022-24, T1]. En el país hay unas **15.000 ferreterías** [Data, CAFARA 2023, T2, viejo].
2. A $70.000 por mes, todo el país vale **USD 8–13 M por año** [Estimate]. Alcanza para un negocio rentable de dos personas, no para una historia de capital de riesgo, salvo que sumen rubros o países [Opinion].
3. **El límite real no es el mercado, es cuántos locales pueden vender e instalar dos personas**: unos 30–40 al año 1 [Estimate, 4 altas/mes, 4–6% de bajas/mes].
4. La demanda del rubro está **floja**: CAME −3,4% interanual en octubre 2026 y Construya −9% [Data, T2]. Lo que aguanta es **la refacción y el repuesto**, que es lo que vende una casa de sanitarios [Data, CAME vía Los Andes 08/11/2026].
5. Hay que **salir a vender**: nadie busca este producto en Google [Data, Trends AR, T1].

## Tamaño
Un solo método para todo: **comercios del rubro × los mismos dos filtros**. Los filtros son: atiende por WhatsApp (70% [Assumption]) y tiene la lista en Excel o sistema y cobra formal (40% [Assumption]). Juntos dan 28%, y es el supuesto más débil del análisis.

| Nivel | Cuenta | Resultado | Confianza |
|---|---|---|---|
| **TAM** (país) | 15.000 ferreterías [Data, CAFARA 2023, VIEJO] a 25.000 puntos de venta [Data, ExpoFerretera **2017, VIEJO**] × $70.000 × 12 | ARS 12.600–21.000 M/año ≈ **USD 8–13 M** | Baja-media [Estimate] |
| Total del rubro en CABA | 1.181 ferreterías + 390 sanitarios/plomería + 265 corralones [Data, RUS GCBA 2022-24, T1] | **1.836** | Alta en el conteo; puede haber cierres desde el relevamiento |
| **SAM CABA** (solo rubros que encajan) | 390 sanitarios/plomería (bajo) o + 265 corralones (alto) × 28% | **~110–185** locales | Baja [Estimate, filtros sin dato] |
| **SAM AMBA** | 4.570–7.620 comercios (proxy por población) × 36% que son sanitarios/corralones (proporción de CABA) × 28% | **~460–770** locales | Baja [Estimate] |
| **SOM año 1** | 4 altas/mes [Assumption], 4–6% de bajas/mes [Data T3, no es del segmento] | **30–40** locales ≈ ARS 25–34 M/año | Baja-media [Estimate] |
| Techo con venta en persona | altas ÷ bajas | **~67–100** locales (100 con 4% de bajas, 67 con 6%) | Baja-media [Estimate] |

**Qué dice el censo.** El proxy por población daba ~1.700 comercios del rubro en CABA; el censo cuenta 1.836. **El censo confirma el proxy.** Los ~475 que se habían estimado antes eran un número ya filtrado y con ferreterías de barrio adentro, que no encajan.

**Consecuencia importante [Opinion].** 30–40 locales en el año 1 equivalen al **16–36% de todo el SAM de CABA**. Llegar ahí exige alguna de tres cosas:
- convertir a muchísimos de los de Capital;
- sumar ferreterías grandes con sanitarios;
- salir de CABA (GBA o a distancia) antes del mes 12.

CABA alcanza para los primeros 10 locales, no para el año entero.

## Trayectoria
- **A favor:** WhatsApp es el canal de compra (74–86% de los argentinos lo usa con empresas [Data, Meta vía Cronista, fuente interesada]). La inflación de 1,7–1,9% mensual deja las listas viejas, que es justo el dolor que el producto resuelve [Data, INDEC/REM].
- **En contra:** obra en baja (permisos −10,9%, loza sanitaria −8,2% [Data, INDEC]), el 71,4% de las ferreterías vendió menos [Data, CAFARA sep-2026] y la mora de las pymes viene en alza [Data, BCRA vía prensa].
- **Madurez:** creciente en oferta (muchos lanzamientos 2025-26), temprana en adopción del rubro [Opinion].

## Economía unitaria (insumo para la fase 7)
| Línea | ARS/mes por local | Etiqueta |
|---|---|---|
| Precio | 70.000 | [Data, decisión del founder] |
| IA (USD 10 × MEP 1.578,78) | −15.788 | [Estimate, costo no medido] |
| Comisión de cobro del abono (MP 6,29% + IVA) | −5.320 (0 si paga por transferencia) | [Data T3] |
| **Contribución** | **≈ 48.900 (70%)** | [Estimate] |

- **Bajas mensuales de referencia:** 4% base, 6% pesimista [Data T3, no es del segmento].
- **LTV:** ARS 0,8–1,2 M [Estimate].
- **Ojo con la contribución:** depende del costo de IA, que no está medido [Assumption] y sube con el volumen de mensajes del local. Un local muy activo puede gastar el doble o el triple de USD 10.
- **CAC tolerable:** hasta ARS ~400.000 por local. Hoy cuesta casi cero en plata, pero insume 10–20 horas de los socios por local [Estimate].
- **Tipo de cambio:** MEP $1.578,78 (06/11/2026) [Data, 4 fuentes coinciden, alta]. `founder/cfo.md` usa $1.450 y $35.000: hay que actualizarlo.

## Regulación (resumen; detalle en `raw/regulatory.md`)
| Tema | Qué hay que hacer | Costo | Cuándo |
|---|---|---|---|
| Facturación | **Un solo monotributo** (el de Mati) + acuerdo de socios firmado. Si dos facturan por separado, ARCA puede ver una sociedad de hecho | Cuota cat. A $49.527 [Data T1, ARCA] + IIBB CABA ~$30.025 [Data T3] ≈ $79.500/mes. **Mati ya lo paga por su trabajo**: el costo extra puede ser 0 hasta que cambie de categoría [Assumption, confirmar con un contador] | Antes del primer cobro |
| Datos personales | Inscribir la base en la AAIP. Contrato con el local: materialIA es "encargado" (art. 25, Ley 25.326); no se entrena con datos de clientes | Gratis por TAD | Antes del primer cliente |
| Papeles | Términos, privacidad, contrato y acuerdo de socios | ARS 0,5–1,35 M con abogado [Assumption, sin fuentes de honorarios] | Antes del primer pago |
| Meta | Bot acotado al negocio y con pase a humano (la IA tiene que ser "auxiliar") [Data T1, términos de Meta 23/09/2026]. Verificación del negocio con web y dominio para ser Tech Provider | USD 15–30/año de dominio [Estimate] | Antes de conectar locales por Embedded Signup |
| Mercado Pago | OAuth con la cuenta de cada local. Un eventual porcentaje sobre ventas requiere acuerdo comercial y revisión profesional; no se deduce una condición jurídica sólo por cobrar o no comisión [Pendiente] | A verificar | Antes de contratar |
| SAS | Cuando haya ~15–20 locales pagando. Suma ARS 250–600 mil/mes [Estimate T3], más IVA 21% e IIBB 3% [Data T3] | — | Mes 6–12 |

**Riesgo regulatorio global: MEDIO.** El riesgo que puede matar el proyecto es depender de Meta, no la ley local.

## Geografía
- **Mercado 1:** CABA eje oeste-centro.
  - **Av. Juan B. Alberdi 3400–3999:** 29 sanitarios + 16 cerámicas en 6 cuadras, unos 70 comercios del rubro en 2 km [Data, RUS].
  - Flores/Caballito y Once.
  - Pobreza en CABA: 11% contra 37% en el conurbano [Data, INDEC].
- **Mercado 2** (desde junio 2027): venta a distancia en Córdoba → Rosario → Mendoza → Neuquén, más el GBA.
- **Mercado 3** (2028): mayoristas, cuando el producto tenga listas por cliente y cuenta corriente.
- **Zona sur:** queda como 1b; no hay conteo y está dispersa.

## Momento
- **Ventana de venta:** hasta el 19/12/2026 (3–5 pilotos), y después de marzo a junio de 2027. Diciembre-febrero es malo [Data T2 / Assumption].
- **Ventana competitiva:** **6–24 meses, escenario central 12–18**, antes de que Meta o Tiendanube lleguen a comercios sin tienda [Opinion; rango que une las estimaciones de los agentes B2 (6–18) y A2 (12–24)].

## Data gaps
- Conteo oficial por código de actividad en el AMBA (el CSV de CEP XXI tiene el certificado vencido: bajarlo a mano).
- % de locales con lista en Excel o sistema y que cobran con MP (es el supuesto del 40%, el más débil).
- Volumen y categoría de consultas por WhatsApp (IA y soporte; servicio dentro de 24 h gratuito según la corrección oficial; otras categorías por verificar).
- Bajas, CAC y disposición a pagar del segmento: solo se obtienen con clientes reales.
- Honorarios 2026 de abogados; si Meta verifica a un monotributista.
- Informalidad del rubro: cuántos cobran en efectivo y sin factura (afecta si usan el link de MP).
- Percepciones de IIBB e impuestos al pagar con tarjeta servicios del exterior (IA, Supabase); las fuentes se contradicen.
- Tabla oficial vigente de comisiones de Mercado Pago.
- Si el censo 2022-24 sigue vigente (puede haber cierres): validar en la caminata.

## Conexiones estratégicas
- La caída de la obra (ver `industry-trends.md`) favorece a la casa de sanitarios de repuestos, que es la persona principal (ver `target-audience.md`).
- El techo de ~100 locales con venta en persona explica por qué el canal mayorista (ver `competitor-landscape.md`) es la palanca para escalar.

---

## Flags

**Red Flags:**
- **Dependencia total de Meta.** El canal, las reglas y las tarifas son de Meta, y Meta decide a su criterio qué IA es "principal". Además, una infracción de un cliente puede castigar a materialIA como Tech Provider, y con eso caen todos los locales a la vez. **Hoy mismo la cuenta de prueba y el portfolio están restringidos.**
  - Mitigaciones: bot acotado al rubro con pase a humano; widget web como canal alternativo; cada local con su propia cuenta; apelar y verificar el negocio antes de escalar.

**Yellow Flags:**
- Mercado chico y demanda del rubro en baja.
- El SAM de CABA (~110–185) no alcanza para el SOM del año 1 sin salir de Capital.
- Los costos legales de arranque (ARS 0,5–1,35 M) superan varios meses del presupuesto de USD 100/mes.
- El SAM depende de un supuesto sin dato (40% con planilla).

## Sources
- `raw/market-size.md`, `raw/regulatory.md`, `raw/geographic.md`, `raw/target-audience.md` (todas con links y tiers).
- GCBA RUS 2022-24 (T1); ARCA monotributo (T1); Ámbito, Cronista y El Litoral (dólar, T2); CAME vía BAE y Los Andes (T2); INDEC ISAC/ICC/EPH (T1).
