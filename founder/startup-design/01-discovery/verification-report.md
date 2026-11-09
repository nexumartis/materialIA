# Verification Report: materialia

> **Verificación histórica previa al cierre.** Leer también [correcciones del 09/11](corrections-2026-11-09.md): el supuesto de cargos de servicio de Meta no superó el contraste oficial posterior. La lista y las cuentas siguientes preservan esa revisión original; no certifican el estado corregido ni todas las fuentes.
*Generated: 2026-11-09 — Agente V1 (Verification), fase 3 (01-discovery)*

Documentos auditados: `market-analysis.md`, `competitor-landscape.md`, `target-audience.md`, `industry-trends.md`, `confidence-dashboard.md`. Los archivos de `raw/` se abrieron solo para contrastar números y data gaps.

## Summary
- **Critical issues:** 3
- **Warnings:** 8
- **Info:** 10

---

## Critical Issues
Problemas que pueden llevar a una mala decisión. El proceso se frena acá hasta que el usuario los revise.

### C1. El SAM está calculado con dos métodos incompatibles, y la "contradicción resuelta" compara cosas distintas
- **File(s):** `market-analysis.md` (tabla Tamaño y "Contradicción resuelta"); `raw/market-size.md`; `raw/target-audience.md`
- **Section:** Tamaño
- **Problem:**
  1. **La contradicción no existe tal como se presenta.** Los ~475 de CABA del primer cálculo son un SAM **después** de los filtros (1.700 comercios × 70% WhatsApp × 40% planilla). Los 390 del censo son el conteo **antes** de filtrar, y solo de sanitarios y plomería. El nivel comparable es el total del rubro: el censo da 1.181 ferreterías + 390 sanitarios + 265 corralones = **1.836**, y el proxy por población daba **~1.700**. O sea, el censo **confirma** el proxy, no lo desmiente. El raw `target-audience.md` dice lo mismo: "los ~475 son coherentes con 390 sanitarios más una parte de los corralones".
  2. **El SAM CABA de 150–250 no tiene fuente.** El "40–60% de los 390" no está en ningún raw y no aplica los filtros de WhatsApp y planilla que usa el resto del cálculo. Si se aplicaran (70% × 40% = 28%), los 390 sanitarios darían **~110**.
  3. **El SAM AMBA (2.130) sigue usando el método que se dice descartado.** Parte de 7.620 = 25.000 × 30,5% de la población. Toma la base alta de 25.000 (ExpoFerretera **2017**, VIEJA) y omite la versión baja del raw (~1.280 sobre una base de 15.000). Además incluye a las ferreterías de barrio, que `target-audience.md` excluye ("A quién NO venderle", 72,9% del sector). Con la proporción que se usa para CABA, el AMBA daría del orden de **700–1.100**, no 2.130.
- **Suggested fix:** usar un solo método. Recomendado: censo RUS para CABA × los mismos filtros (WhatsApp y planilla) y solo para los rubros del ICP (sanitarios, plomería, corralones y ferreterías grandes). Para el AMBA, el mismo ratio de CABA o el CSV de CEP XXI. Reescribir el párrafo de "Contradicción resuelta", mostrar el rango bajo y el alto, y marcar la base de 25.000 como VIEJA.

### C2. Depender de Meta está descripto como un riesgo que puede matar el proyecto, pero ningún documento lo pone como Red Flag
- **File(s):** `market-analysis.md`, `industry-trends.md`, `confidence-dashboard.md`
- **Section:** Flags
- **Problem:**
  - `market-analysis.md` dice que "el riesgo que puede matar el proyecto es depender de Meta", pero en Red Flags pone "Ninguno que mate la idea".
  - `industry-trends.md` califica a Meta como "**Riesgo alto**" (cambia términos sin aviso y castiga a toda la organización por infracciones de sus clientes), pero en Red Flags pone "Ninguno nuevo" y lo deja como Yellow.
  - El tablero tampoco lo lista entre los riesgos rojos.

  Quien lea solo los Flags, que es lo que pasa a las fases siguientes, va a subestimar el riesgo más grande que el propio documento reconoce. Esto incumple la regla 5 del protocolo ("No flags" cuando el contenido muestra riesgos).
- **Suggested fix:** subir "dependencia de la API, las políticas y las tarifas de Meta (suspensión de la cuenta Tech Provider = todos los locales caen a la vez)" a Red Flag, en `market-analysis.md` y en `industry-trends.md`, con su mitigación.

### C3. El análisis de precio y de disposición a pagar ignora el costo total que paga el local (abono + Meta)
- **File(s):** `target-audience.md` (Demanda y disposición a pagar, Objeciones); `market-analysis.md` (Economía unitaria); `confidence-dashboard.md`
- **Section:** Demanda y disposición a pagar
- **Problem:** no está en discusión que el local pague a Meta: es la decisión de diseño, y es correcta. El problema es que esa plata sale del mismo bolsillo que el abono, y el análisis de precio no la cuenta.
  - `industry-trends.md` estima que un local activo (~4.800 respuestas/mes) le pagaría ~USD 99 a Meta, ≈ ARS 154.000. Es **más del doble del abono** de $70.000 (USD 44,3).
  - En el escenario medio del raw (1.800 respuestas/mes) son ~ARS 32.000 extra, un **46% más** que el abono.
  - El raw `demand-signals.md` lo advierte explícitamente: "duplica el costo total percibido de materialIA".
  - Aun así, el ancla ("3,5% de un vendedor"), el rango recomendado de $60.000–90.000, la lista de objeciones y el tablero de confianza se calculan solo sobre el abono. Esto puede llevar a fijar un precio que el dueño rechace por el costo total.
- **Suggested fix:** en `target-audience.md`, agregar el "costo total para el local" por escenario (chico, medio y activo) y la objeción "encima le pago a Meta". En el tablero, poner como incertidumbre clave el volumen de mensajes, que define el costo de IA y el de Meta. Llevarlo a las fases 4 y 7.

---

## Warnings
Problemas que bajan la calidad pero no bloquean decisiones.

### W1. Afirmaciones cuantitativas sin etiqueta
- **File(s):** los cinco
- **Problem:** ejemplos sin [Data]/[Estimate]/[Assumption]/[Opinion]:
  - **`market-analysis.md`:** monotributo "Cat. A ≈ $79.500/mes"; costo de la SAS "ARS 250–600 mil/mes, IVA 21%, IIBB 3%"; dominio "USD 15–30/año"; LTV "ARS 0,8–1,2 M".
  - **`competitor-landscape.md`:** casi toda la matriz (Prometheo 600 pymes/USD 700k, Botmaker ~5.000 clientes, Darwin USD 7M+, Chat Nube AR$190–400, "~$2 M/mes con cargas", "71,5% de los emprendedores").
  - **`industry-trends.md`:** VICI, USD 10M en IA, Vambe, Jelou, Pulpos y Meta One USD 14,99.
  - **`target-audience.md`:** Once "32 sanitarios + 74 ferreterías".
  - **`confidence-dashboard.md`:** "la instalación pasa de 2 horas a 2 días".
- **Suggested fix:** etiquetar cada cifra, o agregar una etiqueta por columna en las tablas (por ejemplo, "Precio [Data T1, 09/11/2026]").

### W2. La confianza del SOM y del techo es más alta que la de sus insumos
- **File(s):** `market-analysis.md`, `confidence-dashboard.md`
- **Problem:**
  - El SOM (30–40 locales) y el techo (~100 locales) figuran con confianza **Media**. Pero se apoyan en las bajas del 4–6% (que el tablero califica **Baja**, Tier 3 y de otro segmento) y en 4 altas/mes (supuesto).
  - El techo de ~100 vale solo con 4% de bajas: con 6%, es **~67**.
  - La contribución del 70% depende de un costo de IA de USD 10 que es "**Baja (no medido)**", y que además debería subir con el volumen del local activo.
- **Suggested fix:** bajar el SOM y el techo a Baja-media, mostrar el techo como rango (67–100) y marcar la contribución como sensible al volumen.

### W3. El plazo de Meta aparece con tres valores distintos
- **File(s):** `market-analysis.md`, `industry-trends.md`, `confidence-dashboard.md` (12–18 meses); `competitor-landscape.md` (6–18 meses); `raw/trends.md` (12–24 meses)
- **Problem:** el tablero dice "Meta tarda 12–18 meses — opinión de 2 agentes", pero los dos agentes dijeron 6–18 y 12–24. 12–18 es la intersección, no un acuerdo, y el extremo de 6 meses desaparece de la síntesis.
- **Suggested fix:** usar un único rango (6–24 meses, escenario central 12–18) en los cuatro documentos y aclarar de dónde sale.

### W4. "Ningún SaaS lee la lista que el local ya usa" está sobreafirmado
- **File(s):** `competitor-landscape.md` (Lo que sigue libre, punto 1)
- **Problem:** la misma matriz dice que **Meteor** lee el stock vía Alegra, Shopify o Woo, que **Vendi** "ya tiene el stock del cliente" y que **Vozia** trabaja con stock en vivo. El raw `indirect-competitors.md` muestra plantillas de n8n que leen Google Sheets. Lo libre, en todo caso, es "leer **la planilla de Excel o Sheets** sin migrar, para un local sin ERP ni tienda", y eso es más angosto.
- **Suggested fix:** acotar la frase y reflejar el matiz en el mapa de posicionamiento, donde dice "Libre hoy" en una celda que ocupa Vozia.

### W5. Data gaps del raw que no llegaron a los entregables, y el tablero sin sección de Data gaps
- **File(s):** `target-audience.md`, `market-analysis.md`, `confidence-dashboard.md`
- **Problem:**
  - **Gaps perdidos:**
    - Voz propia de plomeros y gente de obra. El dolor #3 se apoya en ellos (`raw/customer-voice.md`).
    - No hay ninguna cita sobre cobro y verificación de pagos, que es parte central del producto.
    - Informalidad del rubro (`raw/market-size.md`, `raw/geographic.md`); afecta la adopción del link de MP.
    - Percepciones de IIBB e impuestos sobre servicios digitales del exterior; afectan el costo de IA pagado con tarjeta (`raw/regulatory.md`).
    - Tabla oficial de comisiones de MP.
    - Norma sobre información de precios en canales de mensajería.
  - **Sección faltante:** `confidence-dashboard.md` no tiene una sección "Data gaps". "Lo que no sabemos" y "Lo más flojo" cumplen parte de la función, pero no con el formato del protocolo.
- **Suggested fix:** sumar esos gaps a los entregables correspondientes y renombrar o agregar "Data gaps" en el tablero.

### W6. Datos de más de 18 meses sin marcar como viejos
- **File(s):** `market-analysis.md`, `competitor-landscape.md`, `target-audience.md`, `confidence-dashboard.md`
- **Problem:**
  - El techo de 25.000 comercios del TAM sale de ExpoFerretera **2017** y no está marcado.
  - "Botmaker ~5.000 clientes (2022)" no está marcado como viejo.
  - Las citas de Angiulli/CAFARA (2023) y los "20.000 artículos" (CAFARA 2023) tampoco.
  - El RUS 2022–24 tiene confianza **Alta** sin advertir que, con un 71,4% de locales vendiendo menos, puede haber cierres desde el relevamiento.
- **Suggested fix:** marcar "VIEJO" donde corresponde y agregar al RUS la nota "conteo 2022–24; validar en la caminata".

### W7. Fuentes repetidas presentadas como corroboración
- **File(s):** `confidence-dashboard.md`, `competitor-landscape.md`, `target-audience.md`, `market-analysis.md`, `industry-trends.md`
- **Problem:**
  - "~15.000 ferreterías: 3 fuentes": las tres son CAFARA (2019–23), así que es **una** sola fuente. Con eso y siendo vieja, corresponde Media-baja.
  - Prometheo "USD 700k/año" tiene una sola fuente (Cronista), y iProUP dice USD 300k. El tablero lo marca, pero `competitor-landscape.md` y `target-audience.md` (USD 97 por cliente) lo usan sin la advertencia.
  - "74–86% usa WhatsApp con empresas" y "8 de cada 10 lo prefieren" son ambos de Meta.
- **Suggested fix:** contar fuentes independientes y llevar la advertencia de Prometheo a los dos documentos que lo citan.

### W8. El estado de la fuente de precios de Meta no coincide entre documentos
- **File(s):** `industry-trends.md`, `confidence-dashboard.md`, `competitor-landscape.md`
- **Problem:**
  - `industry-trends.md` dice "3 fuentes no oficiales; falta la tabla oficial" para todo el cambio del 01/10/2026. Pero la regla de 1.000 mensajes gratis sale de Meta for Developers (T1), según el raw y el tablero ("1 oficial + 3 de terceros"). Lo no oficial es solo la tarifa de USD 0,026.
  - `competitor-landscape.md` pone el precio del agente de Meta como "Gratis o centavos (contradictorio)" y lo lista como data gap. Sin embargo, el raw `trends.md` trae datos T1 (USD 0,04–0,05 por mensaje del agente vía API, desde el 01/08/2026) y T2 (Meta One USD 14,99–499 en la app).
- **Suggested fix:** separar "regla" (T1) de "tarifa" (T3) en trends y actualizar la fila de Meta en la matriz con los datos del raw.

---

## Info
- **Cuentas verificadas sin errores:**
  - TAM: 15.000–25.000 × $70.000 × 12 = ARS 12.600–21.000 M ≈ USD 8,0–13,3 M.
  - IA: USD 10 × 1.578,78 = $15.788.
  - MP: 6,29% + IVA ≈ $5.328.
  - Contribución: $48.892 (69,8%).
  - LTV: 48.900 / 6% = 0,82 M y 48.900 / 4% = 1,22 M.
  - CAC ≈ LTV/3.
  - SOM: con 4 altas/mes y 4–6% de bajas, a los 12 meses quedan 35–39 locales.
  - SAM AMBA: 7.620 × 0,7 × 0,4 = 2.133.
  - Meta: 3.800 × 0,026 = USD 98,8.
- **Consistentes en los 5 documentos:** precio $70.000; MEP $1.578,78; 390/1.181/265 en CABA; Alberdi (29 sanitarios, ~70 comercios); CAME −3,4%; Construya −9%; 71,4% vendió menos; AWAM USD 29.
- **Monotributo:** "Cat. A ≈ $79.500" en `market-analysis.md` es la suma de $49.527 (ARCA) + $30.025 de IIBB (T3), como en el tablero. Coincide, pero conviene no llamar "Cat. A" al total.
- **"Gasto fijo de ~$5 M/mes"** (dolor #6) es el costo total de una ferretería de barrio de La Plata, que es el segmento excluido. No contradice los ~$2 M de un vendedor, pero conviene aclararlo para que no se lean como la misma métrica.
- **IVA e IIBB con la SAS:** si el precio de $70.000 queda como precio final, la contribución cae ~20%. Tenerlo en cuenta en la fase 7.
- **`founder/cfo.md`** usa $1.450 y $35.000. Ya está señalado en `market-analysis.md`; queda pendiente actualizarlo, y está fuera del alcance de esta verificación.
- **El 66% con hasta 5 empleados** sale de una muestra de n=47. Conviene mostrar el n donde se cite.
- **Reseñas del comprador:** `target-audience.md` suma 6+3+3 = 12 y el tablero dice "12+". Coinciden.
- **Diseño, no error:** el costo de los mensajes de Meta lo paga cada comercio, porque es dueño de su cuenta. No se marca como error. C3 trata solo del impacto en la disposición a pagar.
- **Cross-phase:** las fases 4–8 todavía no existen. Lo que hay que trasladar: el SAM corregido (C1), el Red Flag de Meta (C2) y el costo total del local (C3) a Lean Canvas, pricing y riesgos.

---

## Verification Checklist
- [ ] All quantitative claims labeled — *no (W1)*
- [ ] No internal contradictions found — *no (C1, W3, W4, W8)*
- [ ] Confidence ratings consistent with evidence — *no (W2, W7)*
- [ ] Data gaps declared in all deliverables — *parcial: falta la sección en el tablero y hay gaps perdidos (W5)*
- [x] Red/Yellow flags present in all deliverables — *están presentes en los cinco; ver C2 por la clasificación*
- [ ] No stale data unmarked — *no (W6)*
- [ ] No duplicate-source false corroboration — *no (W7)*
- [ ] Strategy reflects market data (cross-phase) — *no aplica todavía (sin fase 4)*
- [ ] Product reflects customer pains (cross-phase) — *no aplica todavía (sin fase 6)*
- [ ] Financial reflects business model (cross-phase) — *no aplica todavía (sin fase 7)*
- [ ] Validation covers identified risks (cross-phase) — *no aplica todavía (sin fase 8)*
