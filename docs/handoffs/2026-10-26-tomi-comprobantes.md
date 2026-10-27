# Primera tarea para Tomi / su Claude

**Estado: OCR iniciado, no integrado ni aprobado.** El usuario pidió cerrar la sesión, dejar esto como primera tarea para Tomi y conservar todo en main. Para evitar activar código con revisión pendiente, sus seis fuentes y dependencias están íntegros en [ocr-t1-source.zip](comprobantes/ocr-t1-source.zip), fuera del runtime y de la suite normal del backend. El ZIP tiene manifiesto de hashes y su propio parche de dependencias; el pyproject de referencia no debe sobrescribir el vigente.

## Pedido acordado

Sólo comprobantes de **pagos de clientes**, no gastos/proveedores. Recibir imagen/PDF en chat web, leer con OCR y registrar el mes; con pago verificado, emitir una constancia comercial de la compra y entregarla en el chat. Una foto no acredita dinero. Transferencias requieren cotejo bancario y revisión auditada del dueño; Mercado Pago conserva verificación por proveedor. No es facturación fiscal ni integración WhatsApp/email.

## Por dónde seguir

1. Leer AGENTS.md, CLAUDE.md y docs/current-state.md. Usar **Ponytail full** y las skills pertinentes por fase; un owner por archivo y revisor en contexto fresco. Trabajar en rama.
2. Leer [alcance acordado](comprobantes/alcance-acordado.md), [plan de continuación](comprobantes/plan-continuacion.md), [evidencia T1](comprobantes/evidencia-ocr-t1.md) y [revisión de Codex](comprobantes/revision-ocr-t1.md). Restaurar fuentes desde el ZIP en la rama de trabajo y fusionar dependencias con cuidado. Es un checkpoint, no una aprobación para ejecutarlo con datos reales.
3. **Primero resolver los cuatro hallazgos de T1:** deadline total que incluya espera de semáforo y máximo de 60 s; completar/validar aislamiento de red anunciado (el bloqueo Python actual no garantiza aislamiento del SO); importe extremo sin excepción Decimal; referencia que no cruce páginas. Comprobar dimensiones finales del PDF y corregir afirmaciones de prueba que excedan la evidencia. Revisión nueva antes de integrar.
4. Continuar T2–T4: migración nueva 0007; confirmación manual auditada que reutilice pagos/stock e impida usar una referencia en dos pedidos; constancia y mensaje idempotentes en la misma transacción, PDF bajo demanda; documentos privados, OCR/worker, registro mensual/CSV y panel/chat. La matriz está en el plan. No agregar broker/equipo de agentes ni servicios pagos si no hacen falta.
5. Probar OCR real y dinero/aislamiento/concurrencia, PDF real y flujo de navegador; registrar fallos y límites. Actualizar estado y revisión antes de publicar/integrar.

## Lo que ya existe

T1 funcionó localmente en Windows con **20 pruebas aprobadas**, incluyendo OCR real de PNG/JPG y PDF digital/escaneado/mixto, formatos argentinos y entradas rechazadas. Eso no resuelve los cuatro hallazgos de revisión. RapidOCR 3.10.0 trae modelos PP-OCRv6 small multilingües; hashes fijados, sin descarga al procesar. Dependencias/modelos no están copiados desde la PC de Matías: están declarados en el checkpoint para reproducirlos. No hubo documentos bancarios reales.

## Nube y precauciones concretas

Tomi informó 0001–0005 y datos demo en Supabase remoto. No se verificó independientemente: la conexión MCP de esta sesión no tenía permiso de lectura. No modificamos nube ni DATABASE_URL/SUPABASE_URL del usuario. La privacidad del chat de PR #12 requiere **0006**; este futuro corte agregará 0007. Verificar versiones y contar con instrucción expresa antes de migrar remoto. Mantener pruebas/reset/seed sólo en DB local descartable. Contraseñas en el mecanismo local de secretos, fuera de Git y de reportes.

En este entorno el almacenamiento propuesto para originales es bytea privado en Postgres con RLS, **atajo sólo para demo pequeña**; cambiar a almacenamiento privado adecuado antes del piloto real. La retención de datos reales está pendiente. La constancia jamás debe generarse por OCR exitoso, ni anunciar entrega antes de persistirla. Revisar el fallo detectado en `_record_payment` al reutilizar referencia en otro pedido.

## Mensaje listo para Claude

> Leé AGENTS.md, CLAUDE.md, docs/current-state.md y docs/handoffs/2026-10-26-tomi-comprobantes.md. Continuá la primera tarea de comprobantes de pagos de clientes con Ponytail. Empezá por resolver y volver a revisar los cuatro hallazgos del motor OCR guardado; después integrá registro mensual y constancia siguiendo el alcance y plan. Trabajá en rama, con revisión en contexto fresco y pruebas locales. No apliques migraciones remotas ni envíes mensajes reales sin mi instrucción expresa.
