**APROBADO para el snapshot post R3**, código y documentación, con el alcance que detallo abajo. Hice sólo lectura estática: no ejecuté pruebas, navegador ni hashes. Lo que confirmé es que el manifest en `docs/reviews/` es igual a `final-review-manifest.json`, y que `llm_sales.py` tiene `_keep_delivered_offer` en la línea 503, su llamada en la 656 y ya no tiene el retorno temprano.

## Código (`review-final-delta.patch`, sólo `llm_sales.py`)

- **El P1 que marqué quedó resuelto.** Ya no está el bloque `if turn.products or turn.state.get("offer"): return _fallback(...)`. La respuesta del modelo vuelve a pasar por `problem()`, la reescritura sin herramientas, la traza `control` y `_fallback`. La lista parcial la sigue frenando `_renumbered`.
- **Propuesta entregada (hallazgo 2).** `_keep_delivered_offer` corre sólo con la respuesta ya aceptada:
  - **Con tarjetas:** la propuesta se conserva si es de una unidad y todos sus productos están en tarjetas con el botón «Agregar». `_ui` arma las tarjetas desde `turn.products` en el mismo orden, así que el `zip` es correcto. Esto respeta el contrato de la spec.
  - **Sin esas tarjetas:** hace falta una pregunta explícita con la cantidad de la propuesta. Si no, se borra y el «sí» siguiente no agrega nada.
  - **Productos:** se reducen a los nombrados o citados que existen en `inventory.offers(turn.tenant, …)`, filtrado por tenant.
  - Cuando falla una condición no muta nada, que es el lado seguro.
- **Sin cambios.** El stock, la confirmación, el pago verificado, el dry-run y el tenant no se tocan. `add_plan()` está cacheado, así que llamarlo ahí no tiene efectos.

## Evidencia de otros, no mía

- **Suite (root):** `root-final-suite-r3.log` termina en «269 passed, 2 warnings in 62.71s».
- **UI (Codex en contexto separado):** el reporte de 6 mensajes coincide con la spec: $96.700, «la nro3» con lista vigente de dos aclara sin mutar, y T6 en mock declarado.

## Documentación

Las cuatro piezas son honestas:
- `current-state.md`, la review y la transcripción de UI.
- `ROOT-VERIFICATION.md` registra el historial rojo: 3 y 5 fallos intermedios.
- `IMPLEMENTATION-REPORT.md` quedó marcado como histórico.

Declaran la aceptación íntegramente live como incompleta, los límites heurísticos y que la migración 0007 no se verificó en remoto. La captura enlazada existe.

## Cosas a tener en cuenta que no bloquean

1. **Canales sin tarjetas.** El contrato de tarjetas existe sólo en la web. Cuando llegue WhatsApp, todas las propuestas dependerán de la pregunta explícita, cuya lista de frases es corta. Va a borrar propuestas válidas, como «¿Te agrego las 3?», y pedir de nuevo. No es inseguro, pero conviene medirlo en ese corte.
2. **Semántica de `mode`.** T6 sale `mock` aunque el modelo respondió, porque se descartaron la respuesta y la reescritura. El reporte histórico decía «`live` si el modelo respondió al menos una vez». La semántica vigente, «mock si el texto no es del modelo», es la más honesta: dejala escrita en una línea en la review.

## Al publicar

Actualizar sólo dos cosas:
- `docs/current-state.md:9` («Revisión final… pendiente»)
- `docs/reviews/2026-10-28-venta-confiable.md:3` («revisión final… pendiente»)

Las líneas finales de la transcripción de UI y de `codex-final-ui/report.md` («La code review de Claude sigue pendiente») son evidencia con fecha: se pueden dejar con una nota de que la revisión ya cerró.

Nota del orquestador sobre mode: la implementación requiere que run devuelva respuesta y que el modelo haya respondido para marcar live. Puede devolver contenido canónico con live; por eso el indicador por sí solo no certifica redacción libre. La transcripción registra los modos reales. Esta precisión documental no modifica el código revisado.
