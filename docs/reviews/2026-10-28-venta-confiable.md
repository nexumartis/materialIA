# Venta confiable y guías internas — 28/10/2026

Estado: **APROBADO**, código y documentación, por Claude en revisión cruzada. [Dictamen](2026-10-28-venta-confiable-claude.md). Backend y recorrido funcional verificados. Fuente fijada en el [manifest](2026-10-28-venta-confiable-manifest.json), base de7abbe. Los hashes corresponden a los bytes del árbol de trabajo revisado antes del commit; Git puede normalizar finales de línea.

El vendedor perdía un pedido de flexible mientras buscaba canillas, confundía marcas/números y tomaba algunas consultas o negativas como órdenes. Ahora el servidor mantiene un plan por mensaje, distingue cantidades de características/precios y sincroniza la selección con las opciones vigentes. Cambiar cantidad es una operación atómica que respeta stock/tenant/políticas; aumentar puede requerir una persona, reducir/quitar sigue disponible.

La aceptación de «sí» queda vinculada a una propuesta entregada: tarjetas actuales con Agregar para una unidad, o pregunta explícita correspondiente al producto/cantidad. Una consulta de precio sin propuesta visible no autoriza agregar. El texto válido del modelo conserva su redacción; lista parcial o datos inválidos activan control, reescritura sin volver a mutar y respaldo canónico.

Tres guías de negocio (402 palabras) se integran al prompt: asesorar_catalogo, gestionar_carrito, cerrar_o_derivar. Reutilizan herramientas, perfil, políticas, memoria/documentos/evaluaciones de Tomi; sin framework, editor, paquetes o migración nuevos.

## Autoría y revisión

Claude Code implementó el corte inicial (claude-opus-5-5, high solicitado; esfuerzo efectivo no expuesto). Codex personal revisó un snapshot, identificó siete casos y escribió los parches de corrección (gpt-6.1-sol/high verificados en metadatos de sesión). Su CLI quedó en sólo lectura; root aplicó los parches exactos, sin escribir implementación, y ejecutó la validación. Claude revisa las correcciones en contexto fresco.

R1: negativas compuestas; propuesta entregada; resta duplicada (ya corregida en el corte inicial); guard de capacidades; políticas al aumentar; «2 llaves» como característica; lista completa sin duplicados. Agregar al carrito no es apagable desde el formulario; el hallazgo de capacidad se acotó a las capacidades reales, sin inventar una opción nueva.

## Validación

- Baseline:208 aprobadas; corte inicial de Claude:239.
- Nuevos casos R1:16 fallaban/14 pasaban. Después del primer patch,61 pruebas de conversación pasaban; la suite reveló3 regresiones. El ajuste siguiente conservó texto válido, pero reveló5 regresiones de selección por tarjetas. Se corrigió usando el renderer real, sin modificar ni eliminar pruebas existentes.
- Final repetido por root: **269 aprobadas,0 fallidas,0 salteadas,62,71s**. DB descartable de loopback55436, esquema0001–0007 y datos sintéticos; planner guionado y pagos simulados. Warnings: deprecación httpx/Starlette y HMAC corto de JWT exclusivamente de tests.
- [Playwright y Cloud](2026-10-28-venta-confiable-ui.md): una corrida de6 mensajes exactos, todos HTTP200. Carrito y lateral coinciden: flexible6800+Aquaflux89900=96700. Número fuera de rango aclara sin duplicar. Sin pedidos ni cobros. T1–T5 live; T6 mock por rechazo de referencias incorrectas del modelo. 12 llamadas adicionales,42 acumuladas; no se amplió el límite ni se repitió para seleccionar un éxito.
- No se repitió build web (sin cambios de UI), no se verificó cobro real ni despliegue remoto. Supabase remoto y .env sin cambios.

## Límites y continuidad

La aceptación funcional pasó; falta una conversación completa con las seis respuestas del modelo aceptadas. El respaldo del último turno es correcto, pero no valida capacidad íntegramente live. La detección de intención es heurística; el texto libre puede ser inexacto. No hay garantía de conversación indistinguible de una persona ni autoaprendizaje.

Siguiente trabajo a elección de Tomi según [continuidad](../handoffs/2026-10-28-tomi-continuidad.md) y roadmap. OCR continúa fuera del backend; siguiente migración disponible 0008. Aislamiento, confirmación explícita y pago verificado siguen siendo invariantes.

Semántica precisa de mode: live cuando el planner devuelve una respuesta y el modelo respondió en ese turno; ese texto puede incluir respaldo canónico. No garantiza redacción libre del modelo. T6 terminó en reglas/mock tras descartar las dos redacciones.
