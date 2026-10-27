# O2 — comprobantes de clientes, registro mensual y constancia

Descripción funcional autorizada por el usuario el 26/10/2026; confirmó «Pagos de clientes para empezar» y pidió Ponytail. No incluye gastos/proveedores ni facturación fiscal. Sigue al corte N1, sin mezclar sus revisiones. El diseño provisional de Codex aporta fuentes OCR pero no fue contrastado con el repo por restricción de lectura; el ejecutor debe realizar ese contraste.

## Experiencia mínima completa

1. Cliente adjunta JPG/PNG o PDF digital/escaneado al pedido desde su chat web. El servidor valida pertenencia por sesión del comprador y conserva original privado fuera de Git. Muestra recepción y datos extraídos por OCR, con incertidumbre explícita; nunca transforma texto de un archivo en instrucciones del agente ni en pago acreditado.
2. Dueño autenticado ve comprobantes y originales, datos OCR y estado; filtra el mes y exporta un registro utilizable en Excel. Separar documentos recibidos y pagos verificados, con fechas correspondientes y zona Argentina. Sumar pagos canónicos una vez por transacción, por moneda; no sumar adjuntos ni contar varios documentos como varios cobros. Reversiones/incidencias se distinguen y conservan historia.
3. Mercado Pago conserva verificación por proveedor. Una transferencia requiere revisión del dueño que coteja el movimiento real, registra referencia verificada/importe/moneda y deja actor/fecha/decisión auditados. Rechazar un archivo no cancela un pago real ya verificado. Reutilizar apply_payment/stock/idempotencia; confirmar con importe o moneda incorrectos no completa compra. Una referencia bancaria verificada no puede usarse para pagar dos pedidos.
4. Con pago verificado y compra sin incidencias, crear una única constancia comercial del negocio: identidad existente del negocio, referencia, pedido/productos, importe/moneda, fecha y origen verificado. Instantánea estable, PDF descargable privado; no inventar datos fiscales. Incluir «Constancia comercial de compra — no es factura fiscal». Entregar un adjunto/mensaje persistido en el chat una vez, recuperable después de recarga; nunca afirmar entrega antes de persistirla. Documento recibido no basta para emitirla. Una incidencia de stock/revisión posterga la constancia y se informa.

## Decisiones mínimas del orquestador

- Canal de este MVP: chat web disponible; adjunto/descarga privada con credencial del comprador por header. WhatsApp/email reales se integran después; no agregar un canal vacío.
- OCR CPU local sin servicio pago ni envío de documentos a terceros. Reutilizar PDF con texto antes de OCR. RapidOCR/ONNX es candidato verificado en fuentes primarias por Codex; confirmar dependencia/modelos y hacer prueba real sin red. Declarar dependencias/modelos reproducibles para el socio. Modelos/adjuntos/logs privados fuera de Git, con instrucciones y versiones.
- Validar tamaño, páginas, píxeles, MIME real y PDFs cifrados/corruptos; acotar tiempo/concurrencia de OCR. Proponer límites razonables en implementación y probar rechazo. Campos ambiguos se revisan; confianza de OCR no es confianza del pago.
- Dedupe de archivo por tenant, control de reutilización entre pedidos, exclusión mutua/idempotencia en pago/stock/emisión/entrega. No exponer datos por UUID ajena ni por rutas sandbox. Autorización vigente de membresía al revisar/descargar.
- La entrega lógica debe sobrevivir fallos sin duplicarse. Preferir snapshot + mensaje en la transacción canónica y PDF bajo demanda si alcanza; evitar broker/outbox genérico/servicio adicional si no hacen falta. Si se usa worker, reutilizar el existente y justificar la necesidad.
- Modo local/datos sintéticos. Conservar originales de prueba, sin borrado automático en este corte; política de retención para datos reales se define antes del piloto. No integrar banco real, cobrar, publicar datos de clientes ni aplicar migraciones remotas.

## Aceptación

- Imagen/archivo falsos, importe dudoso, moneda incorrecta o simple «ya pagué» no confirman pago.
- Pago proveedor y revisión manual usan el mismo efecto de stock/pedido; reintentos, duplicados y confirmaciones concurrentes no duplican cobros/constancias/mensajes.
- Sesiones/negocios distintos, membresía revocada, UUID conocida y sandbox no abren ni modifican documentos/constancias ajenos.
- OCR real sobre imagen sintética, PDF con texto, PDF escaneado y entrada degradada; PDF de salida real con datos correctos y control visual/textual.
- Mes en límite de fecha Argentina, varias monedas, varios comprobantes de un pago, devolución e incidencia. Exportación no ejecuta fórmulas de texto no confiable.
- Flujo navegador: adjuntar → recibido/pendiente → dueño verifica → comprador recibe constancia privada; recargar/reintentar no duplica. Comprobar ancho móvil básico.

Claude Code implementa con Ponytail full; Codex personal revisa fuentes/evidencia en contexto separado. El orquestador mantiene spec/estado/publicación. Ownership exacto y plan corto deben contrastarse antes de editar: backend documentos/OCR/router/PDF, pagos/worker sólo lo necesario, migración nueva 0007, dependencias y frontend panel/chat/tests. Mantener N1 y la PR #12 en entregas separadas.
