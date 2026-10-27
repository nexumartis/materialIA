# Estado actual — materialIA

**Primera lectura.** Contexto operativo breve; consultar el detalle sólo según tarea. Invariantes en [CLAUDE.md](../CLAUDE.md), roles/revisión/cierre en [AI-WORKFLOW.md](AI-WORKFLOW.md), selección de skills en [SKILLS.md](SKILLS.md).

## Fuente y entrega actual — 26/10/2026

Base inspeccionada: `3d0a97a8912c86eded91beecfc90e8eab00e4a9f`, origin/main, PR #11. Ya incorpora cuentas, agente comercial, stock concurrente, carrito/pedidos, proveedor de pago simulado, catálogo CSV, configuración por negocio y tienda pública. El antiguo circuito de mamparas y empresas A/B fue reemplazado por venta de artículos de catálogo C/D; `custom_quote` deriva a una persona.

Entrega R2 implementada y aprobada por revisión cruzada para alcance demo: privacidad del chat público, recuperación por tienda y descarte de respuestas tardías. Claude Code implementó; Codex personal revisó; orquestador documentó. El estado anterior se conserva íntegro en [historial](state-history-2026-10-26.md); sus pendientes y conteos son históricos y deben contrastarse con esta entrega.

## Producto y prioridades acordadas

- Primer producto: ayudar a comercios que hoy usan Excel/WhatsApp a organizar catálogo, fotos, precio y stock; atender/recomendar; gestionar consultas/pedidos y controlar la operación desde el panel.
- Negociación bajo reglas del dueño, intervención humana, cobros/stock/ventas y alertas de reposición son objetivos a especificar en entregas acotadas. No se aprobó implementarlos todos en este corte.
- Diseño/instalación son capacidades adicionales según negocio. Renders/Visual Commerce quedan como ampliación; no son la próxima entrega aprobada.
- Pendiente de decisión: si el panel será registro principal de inventario incluyendo mostrador, o habrá otra fuente sincronizada. Resolver antes de construir ventas manuales/reportes de existencias.
- No hay clientes ni validación comercial registrada. Investigación comercial: toda Argentina. Carpeta comercial/video y revisiones viven en un paquete local externo al repo; sin contactos ni campañas ejecutados. El usuario decidió no agregar contacto público por ahora.

## Evidencia local

V0 sobre la base exacta: 127 aprobadas, 0 fallidas, 0 salteadas con `PV_REQUIRE_DB=1`; `npm ci` + build correctos. Postgres Supabase 17 descartable, loopback; migraciones 0001–0005 y seed sintético. No se probó el servicio Auth completo: usuarios insertados y JWT de prueba firmados localmente. LLM mock y pago simulado.

R1 de Codex personal fue una revisión estática acotada, no auditoría de todo el repo. Detectó pertenencia de conversación, recuperación tras recarga y carrera con reinicio. Claude reprodujo y corrigió los problemas; cerró también vías sandbox sobre pedidos/oportunidades protegidos. Backend final: **136 aprobadas, 0 fallidas, 0 salteadas**. Build correcto y **36 comprobaciones Chrome aprobadas**, incluyendo 390 px; frontend sin cambios después de esa corrida. [Revisión cruzada final aprobada](reviews/2026-10-26-chat-publico-codex.md), sin bloqueos P1/P2 en el paquete fijado. Detalle, límites y reproducción en [reporte](reviews/2026-10-26-chat-publico.md) y [harness](../web/e2e/README.md).

Sesión: token aleatorio por conversación, hash en servidor, header `X-Conversation-Token`, referencia por tienda en sessionStorage. Recupera en la misma pestaña; al cerrarla se pierde la referencia. Sandbox excluye datos de hilos protegidos. Administración demo requiere **SANDBOX_ADMIN=true y APP_ENV=local**; default apagado.

## Remoto y límites

No se inspeccionó ni modificó la DB remota durante esta entrega. El registro previo indicaba 0001–0004 aplicadas y 0005 pendiente; revalidar antes de cualquier actuación. La nueva 0006 de R2 se aplica únicamente en la DB descartable hasta nueva autorización.

Mercado Pago real y por negocio, WhatsApp, transportistas/tracking y automatización de seguimientos no están validados como operación real. Las rutas sandbox siguen siendo demostración. Tokens legibles por JavaScript, sin vencimiento/revocación; conversaciones anteriores a 0006 no tienen prueba de pertenencia. La clasificación de privacidad depende de la conversación asociada: revisar antes de agregar borrado de conversaciones. No declarar el producto listo para producción por pasar las pruebas locales.

## Continuidad y economía de contexto

El orquestador conserva las decisiones y coordina; Claude Code y Codex personal implementan con revisión cruzada. Cada archivo tiene un owner. Usar briefs cortos, lectura selectiva, evidencia en archivos y resultados breves según [economía de contexto](AI-WORKFLOW.md#economía-de-contexto). El socio con sólo Claude mantiene su modalidad de revisión en contexto fresco.

Codebase Memory se regeneró el 26/10/2026 mediante su CLI local: **indexed, 1102 nodos y 4017 relaciones**, fuente cerrada `d2280c4187a93ec7e01db852ffc1536560af4304` (código R2 en `e0e3317`). Se utilizó una copia Git del mismo commit para compatibilidad con WSL; la conexión MCP de esta sesión se cerró, sin impedir exportar el artefacto con la CLI. Consultar [.codebase-memory/artifact.json](../.codebase-memory/artifact.json): el commit que incorpora el grafo y este estado es posterior al indexado.

Modo fast: excluyó docs, web/e2e, migraciones SQL y archivos estáticos. Leer esos materiales directamente según tarea. Git/Markdown conservan decisiones y resultados; el índice no reemplaza esa lectura ni garantiza ahorro de tokens. Entrega en rama `fix/public-chat-continuity`; integración pendiente de aceptación de los socios.

## Próximo paso

Los socios revisan y aceptan la entrega antes de integrarla. Luego elegir una única especificación de operación comercial a partir de los faltantes observados y de la decisión sobre inventario; candidato: bandeja de consultas e intervención humana, todavía por especificar. Revalidar pendientes de despliegue antes de tocar el remoto.
