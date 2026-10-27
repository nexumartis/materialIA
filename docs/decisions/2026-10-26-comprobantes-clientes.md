# Alcance pedido — comprobantes de clientes y constancia de compra

El usuario pidió: recibir comprobantes, extraerlos con OCR, conservar registro del mes y emitir/enviar una constancia de la empresa al completarse la compra. Aclaró que el primer corte incluye **sólo pagos de clientes**, no gastos/proveedores. Solicitó Ponytail; priorizar reutilización y solución mínima completa.

Se mantiene en curso conversación natural; este es un corte separado que requiere su especificación y pruebas. No se implementa por la sola presencia de esta nota.

## Base para la próxima especificación

- Conservar original privado, datos extraídos y vínculo con negocio/pedido; registrar importe, moneda, fecha y referencia cuando sean legibles. Los datos inciertos quedan para revisión.
- OCR reconoce lo escrito; no confirma acreditación. El pago lo verifica el proveedor o una revisión humana auditada contra el movimiento real. Un archivo falso, duplicado o de otro pedido no puede marcar pagado ni disparar otra constancia.
- Registro mensual de documentos y pagos verificados separados, con acceso del dueño y sin sumar dos veces. Conservar fecha de recepción y fecha de pago.
- Constancia de compra del negocio con pedido, detalle, importe y referencia del pago verificado; idempotente por compra/pago y entregable en el canal disponible. Es una constancia comercial; integración de facturación fiscal queda fuera de este alcance.
- Reutilizar la verificación de pagos/idempotencia existentes. El MVP puede usar descarga/adjunto en chat web; integrar WhatsApp/email exige contar con ese canal y validarlo. No afirmar que se envió antes de entrega efectiva.

Pendientes técnicos: formato/limites de archivos, OCR disponible/coste, almacenamiento privado, revisión de transferencias y formato/canal de constancia. Resolver con un diseño mínimo después del corte activo, sin contratar servicios ni usar datos reales por esta nota.

Fuentes primarias consultadas 26/10/2026: Mercado Pago API Reference (consulta de pago tras notificación) y ARCA Comprobantes/Facturación (separación de recibo/factura). Verificar documentación pertinente al implementar; no constituye dictamen fiscal.
