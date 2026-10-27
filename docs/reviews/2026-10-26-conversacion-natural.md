# Conversación coherente — cierre 27/10/2026

Base `6290f60`. Claude Code implementó seis archivos de producto; Codex personal revisó fuentes en contexto separado. El orquestador documentó y coordinó. Ponytail full activo; TDD/debugging/verificación pertinentes. Claude claude-opus-5-5 efectivo, high solicitado (esfuerzo no expuesto); Codex gpt-6.1-sol/high verificados. Su revisión fue estática porque la política de su CLI impidió comandos; esa política se mantuvo.

## Cambio

En el video del socio, tras «Pago confirmado» y «gracias», el agente volvió a pedir pago y ofreció canales sin integración. Contexto y controles ahora usan el estado real y las capacidades disponibles. Esto no demuestra indistinguibilidad de un humano.

- `llm_sales.py`: contexto de pedidos/perfil/fichas, controles estado/producto/importe/stock y acciones/canales, una reescritura sin herramientas y respaldo contextual. Se eliminó la excepción global de totales: un importe atribuido a un producto debe valer para su precio o línea.
- `sales_agent.py`: agradecimiento, estados de varios pedidos, correcciones parciales con presupuesto y comparación/recomendación factual con intervención humana por datos faltantes.
- `payments/service.py` y test: sólo cambia promesa de aviso de despacho por consulta de estado; conserva transacción de pago.
- `tests/test_natural_conversation.py` y `evals/natural_smoke.py`: regresiones y evaluación local acotada.

Conserva consentimiento de compra y evita repetir mutaciones al reescribir. Sin migraciones, cambios de UI/API, integraciones externas ni cambio del modelo por defecto.

## Validación

Regresiones en rojo antes de arreglos: contradicción de pago, capacidades inexistentes, cierres, correcciones y ventajas inventadas. La revisión detectó cinco problemas; se corrigieron y revalidaron los contraejemplos restantes: total de otro carrito o del propio atribuido a un producto, y recomendación inventada con presupuesto. [Aprobación final](2026-10-26-conversacion-natural-codex.md) y [hashes finales](2026-10-26-conversacion-natural-manifest.json).

Suite de Claude y repetición del orquestador: **174 aprobadas, 0 fallidas, 0 salteadas**, sin exclusiones, `PV_REQUIRE_DB=1`, Postgres local descartable 0001–0006, LLM mock/pago simulado. Repetición 49,37 s. Warnings: transición Starlette/httpx y longitud de clave JWT **de prueba local**. Sin documentos bancarios ni cobros reales; usuarios/JWT sintéticos no validan Supabase Auth completo.

Reproducción desde backend con DATABASE_URL de una DB local descartable preparada con migraciones/seed: `PV_REQUIRE_DB=1 LLM_PROVIDER=mock PAYMENT_PROVIDER=simulated python -m pytest -q -p no:cacheprovider`. En PowerShell definir esas variables antes del comando. Reset/seed sólo locales.

Smoke reproducible: `SMOKE_MAX_CALLS=20 SMOKE_CASES=… python evals/natural_smoke.py salida.json`, proveedor Ollama local configurado. Se consumieron 17/20 llamadas con qwen3:8b, conservando timeout/fallos iniciales y comparación factual posterior; 25–132 s/llamada. Logs extensos y entorno descartable quedan locales. No evalúa gpt-oss:120b ni rendimiento de producción.

Build/36 comprobaciones Chrome corresponden a PR #12; no se repitieron sin cambios de frontend/contrato.

## Límites y continuidad

Negaciones, intención, nombres y datos faltantes se controlan con heurísticas: pueden omitir paráfrasis o derivar de más. Fuera de rutas factuales no hay verificación semántica universal de rasgos cualitativos. Con fichas escasas el resultado es austero. Los tests guionados verifican comportamiento, no naturalidad.

Autoaprendizaje pendiente. OCR: [primera tarea de Tomi](../handoffs/2026-10-26-tomi-comprobantes.md), checkpoint sin aprobar/integrar; sus 20 tests son evidencia separada de las 174. Nube y `.env` intactos: revalidar y aplicar 0006 con autorización antes de usar el chat contra remoto.
