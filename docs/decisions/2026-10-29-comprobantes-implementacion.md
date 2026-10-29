# Decisiones de implementación — comprobantes de clientes y constancia

**Estado:** implementado en `main` (PR #16, T1+T2; PR #17, T3+T4). Integrado **sin** la revisión cruzada de Mati; ver [revisión](../reviews/2026-10-28-comprobantes.md). Continúa el [alcance del 26/10](2026-10-26-comprobantes-clientes.md).

Cada decisión indica qué se descartó y qué la haría cambiar.

## 1. Un archivo nunca acredita un pago

El OCR sólo sugiere importe, moneda, fecha y referencia. El pago lo acreditan el proveedor (webhook verificado) o el dueño con `confirm_transfer`, después de cotejar su banco. **Descartado:** marcar el pedido pagado cuando el OCR «coincide», porque una foto se falsifica fácil y la confianza del OCR no es confianza del dinero.

## 2. Transferencia = mismo efecto que un pago del proveedor

`apply_payment` y `confirm_transfer` comparten `_apply`: stock, estado del pedido, constancia e incidencias. Un solo camino evita dos lógicas de cobro que se desincronizan. La transferencia se guarda como `payments.provider = 'transfer'` con `verified_by`/`verified_at` y auditoría del actor.

## 3. Referencia bancaria única por negocio, con el índice existente

El id de la transferencia es `'<tenant>:<REFERENCIA normalizada>'` y choca con `uq_payments_provider_payment` si se reutiliza en otro pedido (409, rollback completo). **Descartado:** un índice nuevo por `(tenant, referencia)`, porque el existente ya lo resuelve sin migrar índices.

## 4. Constancia y aviso en la misma transacción que el pago

La constancia (`receipts`, única por pedido) y el mensaje «¡Pago confirmado!» se insertan junto con el cambio a PAID. Así no se pierden si falla algo después ni se duplican ante reintentos. El CRM y la auditoría quedan fuera (`_after_paid`). **Descartado:** outbox o worker para la entrega, que suman piezas sin necesidad mientras el canal sea el chat web.

## 5. PDF a demanda desde una instantánea

Se guarda un `snapshot jsonb` y el PDF se arma al descargarlo (reportlab, fuente Vera incluida). La constancia no cambia aunque después cambien el catálogo o el nombre del producto. **Descartado:** guardar el PDF, que duplica datos y obliga a almacenar binarios.

## 6. OCR local, aislado y sin servicios pagos

RapidOCR + ONNX en CPU, con los modelos del wheel fijados por SHA256. El lector corre en un subproceso con plazo total de 60 s y sin red a nivel del SO: `sandbox-exec` en macOS, `unshare --net` en Linux. En Windows queda sólo el bloqueo de Python y el resultado lo declara (`engine`). **Pendiente de decisión:** si sin aislamiento del SO el OCR debe negarse a leer.

## 7. Un valor dudoso no se precarga

Un campo con puntaje < 0,90, o con varios valores distintos, queda en `null` con sus candidatos. Surgió en macOS: una imagen borrosa leía la referencia `…105` (real `…101`) con 0,64 y quedaba precargada. **Cambiaría** si el panel mostrara el valor marcado y obligara a confirmarlo uno por uno.

## 8. Originales en `bytea` (atajo de demo)

Los archivos (≤10 MiB, datos sintéticos) viven en `payment_documents.content`, con RLS. **Antes de un piloto real:** pasarlos a almacenamiento privado (p. ej., bucket privado de Supabase Storage) y definir la retención.

## 9. Migraciones: no se modifica una ya integrada

`payment_documents` iba a sumarse a 0008, pero 0008 entró a `main` con el PR #16. Quien la hubiera aplicado no recibiría la tabla, así que quedó en **0009**. Regla para adelante: una migración que ya está en `main` no se edita; se agrega otra.

## 10. Registro mensual

CSV con `;` y BOM para Excel, en hora argentina. Una fila por pago verificado y las devoluciones con signo negativo en su mes. Los comprobantes van en filas aparte y no suman. Las celdas de texto no confiable que empiezan con `= + - @ \t \r` se escapan con `'`.
