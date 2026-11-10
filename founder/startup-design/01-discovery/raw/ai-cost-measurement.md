# Medición de consumo de IA por turno

**Fecha:** 09/11/2026
**Entorno:** base local (Postgres en Docker, migraciones 0001–0034), tienda de prueba "Sanitarios Demo C" (datos sintéticos), canal `web_sandbox`.
**Modelo:** `gpt-oss:120b-cloud` vía Ollama (el que planeaba Tommy).
**Script:** scratchpad `measure_turns.py` (20 mensajes de un cliente, del saludo al pedido con lista de obra).
**Fuente de los números:** tabla `llm_usage` (tokens que informa Ollama: `prompt_eval_count` y `eval_count`).

## Resultado [Data, medido]
| Turno | Mensaje del cliente | Llamadas al modelo | Tokens de entrada | Tokens de salida | Segundos |
|---|---|---|---|---|---|
| 1 | hola | 1 | 2.319 | 63 | 3,9 |
| 2–8 | inodoro, depósito, precio, flexible, llave, grifería | 2 c/u | 4.552–6.004 | 102–488 | 6–9 |
| 9–10 | recomendación, stock | 1 | 3.167–3.205 | 73–139 | 4 |
| **11** | **lista de obra del plomero** | **5** | **18.968** | 1.947 | 24,7 |
| **12** | **cuánto sale la lista** | **5** | **17.983** | 1.388 | 21,6 |
| 13, 15, 16, 20 | descuento, demora, pago, gracias | 1 | 3.136–3.461 | 64–243 | 4 |
| **14** | envío a Floresta | **6** | **21.002** | 1.471 | 25,2 |
| **17** | armame el pedido | **5** | **17.935** | 998 | 19,6 |
| 18 | acordate del inodoro económico | 3 (una falló con error 500 de Ollama) | 11.103 | 549 | 20,0 |
| **19** | pago por transferencia | **5** | **16.701** | 1.690 | 23,3 |
| Fondo | resumen de lo viejo (compactación) | 1 | 1.010 | 421 | — |
| **Total** | 20 mensajes | **51** | **~163.500** | **~11.200** | — |

## Lecturas
1. **El contexto no crece con la conversación** [Data]. El turno 20 usa 3.136 tokens, casi lo mismo que el turno 1 (2.319). La ventana de 16 mensajes + resumen funciona. El piso fijo por llamada (instrucciones + herramientas) es de ~2.300 tokens.
2. **Lo caro son las vueltas de herramientas dentro de un mismo turno** [Data]. Seis turnos con 3–6 llamadas consumen ~104.000 tokens, el **64% del total**.
3. **Problema de calidad en el diferencial** [Data]. Los turnos 11, 12, 14, 17, 18 y 19 terminaron en la misma respuesta genérica ("¡Mirá, tengo esta que te puede servir!" + lista). El control de honestidad descartó dos respuestas del modelo y respondió el plan por reglas. Consecuencias:
   - la **lista de obra**, que es lo que distingue al producto, no se cotizó bien;
   - "¿hacen envío a Floresta?" se contestó con productos.

   Hay que investigarlo antes de mostrar una demo.
4. **Promedio** [Estimate]: ~8.200 tokens de entrada y ~560 de salida **por mensaje del cliente**, en una conversación larga y exigente.

## Costo por local por mes [Estimate]
Supuestos:
- una conversación típica tiene ~6 mensajes del cliente, así que consume ~49.000 de entrada y ~3.400 de salida [Assumption];
- volúmenes de `trends.md`: chico 150, medio 300 y activo 600 conversaciones por mes [Assumption].

| Precio del modelo (USD por millón, entrada / salida) | Chico | Medio | Activo |
|---|---|---|---|
| Barato: 0,15 / 0,60 (precio típico de gpt-oss-120b en proveedores por uso, **a verificar**) | ~USD 1,4 | ~USD 2,8 | ~USD 5,6 |
| Caro: 1 / 5 (modelo comercial de gama media, **referencia**) | ~USD 9,9 | ~USD 19,8 | ~USD 39,6 |

- La estimación de Tommy (USD 10 por local) queda **dentro del rango**. El número real depende sobre todo de **qué modelo se use y de cuántas vueltas de herramientas haga cada turno**.
- **Ollama Cloud** se cobra por suscripción, no por token. El plan Pro de USD 20 "incluye USD 60 de uso", según `founder/cfo.md`, y no está verificado. El costo por local depende de cuántos locales entran en ese cupo.

## Para bajarlo
1. **Menos vueltas por turno:** que la lista de obra se cotice con una sola herramienta que reciba toda la lista, en vez de una búsqueda por producto. Recortaría hasta la mitad del consumo y probablemente arreglaría la calidad.
2. **Caché del prompt fijo** (~2.300 tokens que se repiten en cada llamada), si el proveedor lo ofrece.
3. **Medir en el piloto** con conversaciones reales: esta prueba es larga y exigente a propósito.
