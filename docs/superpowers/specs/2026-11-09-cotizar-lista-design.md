# Cotizar una lista de obra en una sola herramienta — diseño

**Fecha:** 09/11/2026 · **Estado:** implementado en `feat/cotizar-lista`.

## Problema (medido)
Medición del 09/11/2026 con `gpt-oss:120b-cloud`
(`founder/startup-design/01-discovery/raw/ai-cost-measurement.md`): ante «2 inodoros largos,
2 depósitos, 4 flexibles de 40cm, 2 llaves de paso de 1/2, 1 grifería de cocina» el modelo
hace una `buscar_productos` por renglón y agota `MAX_STEPS`. Cuando redacta, multiplica
cantidades y suma: esos importes no salieron de ninguna herramienta, el control de honestidad
descarta la respuesta y el cliente recibe el respaldo genérico de la última búsqueda. Esos turnos
consumen ~64% de los tokens de la conversación.

## Solución
Herramienta del servidor `cotizar_lista(renglones: [{descripcion, cantidad}])`, ofrecida al
modelo junto a las demás (no apagable, como buscar y consultar).

Por renglón (en `_Turn.quote_list`, con `inventory.offers` filtrado por el tenant del
`ToolContext`):
- **Coincidencia estricta:** el producto tiene que contener TODAS las palabras del renglón
  (y sus medidas: «40cm» → «40 cm», fracciones como «1/2»), color/ambiente/talle incluidos.
  Nunca se cotiza un producto «parecido»: si no hay, el renglón dice «no lo encontré».
- Entre los que coinciden: el más económico con precio y stock para esa cantidad; si no, con
  algo de stock; si no, el primero (para informar a pedido / sin precio / sin stock).
- Resultado: precio unitario, cantidad, subtotal y disponible. Stock parcial: se cotiza lo
  disponible y se informa cuántas faltan. Sin stock: no entra en el total.
- A pedido o sin precio vigente ⇒ `requires_human` (la conversación queda en «derivadas»).
- Total = suma de subtotales con precio y stock, calculado por el servidor.

Texto con viñetas (sin numerar, para no confundirse con la numeración de las tarjetas).

## Control de honestidad
`_catalog` suma los renglones cotizados: el modelo puede atribuir a cada producto su precio,
su subtotal y el total de la cotización, y su disponible. Lo demás sigue igual (importes fuera
de la evidencia, renumeraciones, promesas). Si la respuesta no pasa, el respaldo es el texto de
la cotización (no la última búsqueda).

## Prompt
Guía `cotizar_lista` en `sales_skills.py`: lista con cantidades ⇒ una sola llamada con todos
los renglones; responder con renglones y total tal como vienen; si vuelve a preguntar el total,
volver a cotizar (los importes de turnos anteriores no son evidencia del turno).

## Incluido
El arreglo «agotó las vueltas»: al llegar a `MAX_STEPS` sin redactar, una llamada más sin
herramientas (en vez de volcar la última búsqueda).

## Medición (09/11/2026, base local limpia, tenant C sintético)
`gpt-oss:120b-cloud` respondió **402 Payment Required** en todas las llamadas (cupo de Ollama
Cloud agotado): no se pudo repetir la medición con el mismo modelo. Se midió el turno de la lista
con `qwen3:8b` local (otro modelo: los tokens no son comparables 1 a 1, las vueltas sí).

| Turno | Antes (gpt-oss, sin `cotizar_lista`) | Ahora (qwen3:8b, con `cotizar_lista`) |
|---|---|---|
| Lista de obra | 5–7 llamadas, 19.000–27.800 tokens de entrada, respaldo genérico | **2 llamadas**, 6.784 de entrada, lista cotizada con total |
| «¿Cuánto me sale la lista completa?» | 4–5 llamadas, 14.200–18.000, respaldo genérico | **2 llamadas**, 7.180 de entrada, mismo total |

Respuesta del modelo (pasó el control de honestidad): inodoros a pedido (derivado a una persona),
depósitos y llaves de paso de 1/2 no encontrados, 4 flexibles de 40 cm $27.200, grifería de
cocina $68.000, **total en stock $95.200**. Pendiente: repetir la conversación completa de 20
mensajes con `gpt-oss:120b-cloud` cuando vuelva el cupo.

Suite: 550 pasan, 1 falla conocida por fecha fija (`test_booking::test_free_slots_respect_capacity_and_lead`).

## Fuera de alcance
- «Armame el pedido con todo lo de la lista» (agregar todos los renglones al carrito).
- Sinónimos de rubro (depósito ↔ mochila, etc.) y el planner por reglas: sin LLM, una lista
  sigue yendo a la búsqueda de siempre.
- Sin migraciones: usa catálogo, precios y stock existentes.
