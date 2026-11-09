# Tendencias de la industria

> **Actualización del 09/11/2026:** leer [correcciones y límites](corrections-2026-11-09.md) junto con este documento. La investigación es insumo para validar; no acredita entrevistas, precios aceptados ni un piloto real.

**Phase:** 3 — Investigación de mercado (síntesis)
**Project:** materialia
**Date:** 2026-11-09
**Confidence:** Media

---

## Tendencias macro
| Tendencia | Dato | Impacto | Plazo |
|---|---|---|---|
| Obra en baja, refacción estable | Construya −9% interanual en oct-2026 (5ª caída seguida); ISAC +5,1% en sep; loza sanitaria −8,2%, grifería +12,2% [Data, Mercado/INDEC] | Neutro-negativo; favorece al repuesto sobre el corralón | Trimestre: sin mejora esperada |
| Inflación de ~1,8% mensual | IPC sep 1,9%; REM: 2026 cerraría en 30,4%; materiales +1,3% mensual [Data, INDEC/BCRA] | **A favor:** las listas quedan 4–6% atrasadas por trimestre | Sigue en 2027 (1,6–1,7% mensual) |
| Comercio pyme flojo | CAME rubro −3,4% en oct; 71,4% de las ferreterías vende menos [Data T2] | En contra: el dueño recorta gastos fijos | — |

## Cambios tecnológicos
| Cambio | Etapa | Para materialIA |
|---|---|---|
| **El agente de IA de Meta dentro de WhatsApp Business** (AR desde feb-2026; global el 03/06/2026, "closes sales"; Meta One desde USD 14,99) | Temprana a masiva | Amenaza alta para "responder"; baja hoy para stock + pedido + cobro |
| **Respuestas de servicio gratuitas dentro de 24 h** [Data T1, página oficial de Meta consultada 09/11/2026] | Vigente según la fuente consultada | En etapa 1 no aplicar USD 0,026 ni un umbral de 1.000. Presupuestar IA/hosting y verificar por separado otras categorías o intermediarios. |
| **Pagos dentro de WhatsApp:** Brasil y México sí, Argentina sin anuncio | No disponible | Ventana: el link de MP sigue siendo la norma |
| **Comercio agéntico** (compras desde ChatGPT/Claude) | Experimental | Neutro a corto plazo |
| **Audio y foto como entrada** (Chat Nube ya lo hace) | Masiva | Es requisito, no diferencial |

**Contradicción resuelta: quién paga los mensajes de Meta.** El agente A2 calculó el costo como si lo pagara materialIA. En el diseño aprobado (`docs/superpowers/specs/2026-11-08-whatsapp-design.md`), cada local es dueño de su cuenta de WhatsApp y le paga a Meta directo. Ese costo va en la oferta como "costo del local, aparte", no en el margen de materialIA.

**Contradicción resuelta: fecha de llegada del agente de Meta.** Una fuente dice mayo de 2026 (por la fecha de la nota del Cronista) y otras dicen febrero (iProUP, Forbes, 24/02/2026). Le creemos a febrero.

## Inversión y adquisiciones
- **Tiendanube compró VICI** (Argentina, junio 2025) [Data T1/T2, PitchBook, LatamList] e invirtió USD 10M en IA [Data T2, Valora Analitik].
- **Vambe** levantó USD 14M (dic-2025), **Jelou** USD 10M (ene-2026), **Pulpos** USD 5M (fecha sin confirmar) y **Darwin** suma USD 7M+ [Data T2, SiliconANGLE, Cronista, Ecosistema Startup].
- **Lectura** [Opinion]: el capital va a agentes que **mueven plata o cierran pedidos**, que es la apuesta de materialIA. Los grandes compran en vez de construir, así que una startup con tracción en un nicho vertical es adquirible. Nadie levantó plata para el rubro de materiales en AR: está libre, pero no validado.

## Comportamiento
- Los argentinos abren WhatsApp 37 veces por día [Data T2].
- 8 de cada 10 prefieren WhatsApp para hablar con empresas [Data, Meta, interesada].
- Las ferreterías trabajan con "foto por WhatsApp → ¿lo tenés? → vienen" [Data, El Día 13/09/2026].
- En Perú, el 80% de las ferreterías minoristas vende por WhatsApp [Data, 2022, viejo y de otro país].

## Regulación (hacia dónde va)
- **Datos personales:** proyecto 3397-D-2026, estilo GDPR, sin dictamen. Diseñar hoy con contrato de encargado y registro de incidentes deja a materialIA preparada.
- **IA:** no hay ley y no se espera una a corto plazo.
- **Meta:** cambia términos sin aviso (última actualización 23/09/2026) y castiga a la organización entera por infracciones de sus clientes. **Riesgo alto.**

## Qué significa para la startup
1. **Entrar ahora, chico y por WhatsApp, especializado en el rubro.** La ventana es de 6–24 meses, con escenario central de 12–18 [Opinion].
2. **El valor está en conectar el stock y el precio reales y en cotizar listas**, no en "responder con IA", que Meta va a regalar.
3. **Informar los costos aplicables por categoría**, separando el cargo directo de Meta de IA, hosting y posibles intermediarios. Responder con claridad; no limitar respuestas para evitar una tarifa de servicio retirada.
4. **Vender "recuperar ventas que se pierden"**, no "crecer", porque el rubro está en baja.

## Momento
| A favor | En contra |
|---|---|
| Hábito de WhatsApp masivo | El agente de Meta, gratis o barato |
| Listas que se atrasan con la inflación | Obra en baja, comercios recortando |
| Nicho del rubro sin dueño [Opinion] | Dependencia del canal y sus condiciones |
| Pagos en WhatsApp todavía ausentes en AR | Competidores genéricos baratos (AWAM USD 29) |

**Veredicto: neutro tirando a bueno** [Opinion, confianza media].

## Data gaps
- Tarifas oficiales vigentes de las categorías con cargo en AR antes de incorporarlas; para servicio en etapa 1, ver la corrección oficial enlazada.
- Si el agente de Meta lee stock (probarlo con una cuenta).
- Fecha de los pagos de WhatsApp en AR.
- IPC de octubre (sale el 12/11).

## Conexiones estratégicas
- La ventana (escenario central 12–18 meses) se combina con el techo de ~67–100 locales por venta en persona (`market-analysis.md`): hay que conseguir los casos rápido para después vender a distancia y por mayoristas.

---

## Flags

**Red Flags:**
- **Dependencia de Meta.** Puede cambiar condiciones y tarifas, y puede suspender a la organización entera por una infracción de un cliente. Si suspende la cuenta Tech Provider, caen todos los locales a la vez. La cuenta de prueba está restringida desde el 09/11/2026.

**Yellow Flags:**
- Demanda del rubro en baja durante al menos un trimestre.
- El costo de IA y soporte por volumen todavía no está medido. Si se agregan categorías con cargo o intermediarios, cotizarlos aparte; no atribuir ese costo al servicio gratuito de etapa 1.

## Sources
- `raw/trends.md`, `raw/regulatory.md`, `raw/demand-signals.md`.
- INDEC (T1), REM-BCRA (T2), Meta for Developers (T1), TechCrunch, Cronista, Mercado, iProUP (T2), Zernio/Gallabox/Alibaba (T3, tarifas).
