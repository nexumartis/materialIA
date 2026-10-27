**APROBADO**, para los dos bloqueos pendientes y las regresiones de sus correcciones.

- **Totales:** quitar la excepción impide atribuir a la negra mate tanto el total de otro carrito como el de un carrito que también la contiene. Se conserva la validación contra el precio y el importe de línea del producto. La regresión adjunta verifica además que el total genérico del carrito siga permitido.
- **Recomendaciones con presupuesto:** `free_choice` ahora actúa con o sin presupuesto, tanto en la respuesta inicial como en la reescritura. Los contraejemplos de ventajas inventadas pasan a la respuesta basada en ficha; la comparación filtra por presupuesto y contempla buscar nuevamente cuando ninguna opción entra.

No identifico bloqueos remanentes ni regresiones concretas en el delta adjunto.

Revisión estática exclusivamente sobre lo proporcionado; **no ejecuté pruebas**. Los **174 aprobados, 0 fallidos y 0 salteados**, con DB local y sin exclusiones, son evidencia informada por Claude en `suite-final-cierre.log`.

Se mantienen declaradas las heurísticas y la naturalidad limitada; no se evaluó `gpt-oss:120b`. El OCR archivado no integra el runtime y queda para Tomi.