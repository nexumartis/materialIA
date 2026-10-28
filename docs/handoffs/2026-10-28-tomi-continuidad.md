# Continuidad para Tomi — 28/10/2026

Empezar por [estado actual](../current-state.md), [AGENTS](../../AGENTS.md) e [invariantes](../../CLAUDE.md). El estado y el reporte de cierre indican qué quedó validado y qué sigue pendiente; no tomar un log intermedio como aprobación final. La rama de esta entrega es `fix/sales-intent-and-playbooks`.

## Qué entrega este corte

Acciones del carrito con consentimiento, cantidades y selección sobre la lista vigente; pedido compuesto; derivación registrada sin prometer avisos inexistentes. Tres guías internas del vendedor: `asesorar_catalogo`, `gestionar_carrito`, `cerrar_o_derivar`, integradas al prompt. El servidor conserva el control de precios, stock, tenant, políticas y confirmación de compra. No son plugins de desarrollo ni autoaprendizaje.

Diseño y aceptación en la [spec](../superpowers/specs/2026-10-27-venta-confiable-y-habilidades-design.md). Se reutilizó tu arquitectura de perfiles/memoria/documentos/evaluaciones. No hay migraciones nuevas en este corte.

## Cómo seguir con tu Claude

Mensaje de arranque sugerido:

> Leé AGENTS.md, docs/current-state.md y las invariantes de CLAUDE.md. Confirmá la rama/revisión y los cambios locales antes de editar. Consultá sólo las skills pertinentes de docs/SKILLS.md. Quiero elegir la próxima entrega de docs/roadmap.md: primero señalá qué está hecho y qué falta, con alcance y aceptación breves. Implementá una entrega acotada con un owner por archivo y pruebas proporcionales. Usá revisión en contexto fresco según docs/AI-WORKFLOW.md y cerrá actualizando el estado. No migres/resetées la nube ni publiques sin la instrucción correspondiente.

El [roadmap](../roadmap.md) conserva las opciones de producto. No necesitás las otras cuentas de Mati: está prevista la modalidad de Claude con revisión separada. Las credenciales de cada entorno quedan fuera de Git; preparar el `.env` propio a partir del ejemplo, sin copiar secretos de la PC de otro socio.

## Pendientes para elegir

- Bandeja humana completa: hoy existe registro en oportunidades; faltan gestión de la conversación, contacto y notificación real.
- [Comprobantes de clientes](2026-10-26-tomi-comprobantes.md): checkpoint OCR fuera del backend, todavía no integrado/aprobado. La siguiente migración disponible es **0008**, porque la arquitectura incorporó 0007. Una imagen recibida/OCR no verifica un pago.
- Retención y opt-in de memoria, vista/borrado por cliente y PDF en documentos, según el trabajo de arquitectura.
- WhatsApp, Mercado Pago real por negocio y logística siguen requiriendo integraciones y validación propias.

Mati autorizó que elijas con qué seguir. Antes de modificar stock de mostrador/reportes, acordar cuál será la fuente principal del inventario. La atención sigue teniendo límites heurísticos; las guías no garantizan interpretación universal ni validan cualquier frase del modelo.

## Datos y memoria

La demo y las pruebas de este cierre usaron datos sintéticos locales, pagos simulados y una base descartable para pytest. No se cambió Supabase remoto. Verificar sus migraciones antes de conectarlo; no asumir que tiene 0007 porque el archivo existe en Git.

Codebase Memory es derivado. Consultar `commit` y fecha de [.codebase-memory/artifact.json](../../.codebase-memory/artifact.json); modo fast excluye docs, migraciones, estáticos y E2E. Leer los Markdown directamente. No hace falta recrear el trabajo ni cargar todo el catálogo de skills en cada sesión.
