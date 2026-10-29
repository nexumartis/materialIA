# Estado histórico — cierre 28/10/2026 (antes de comprobantes)

**Primera lectura, cierre 28/10/2026.** Invariantes en [CLAUDE.md](../CLAUDE.md), roles en [AI-WORKFLOW.md](AI-WORKFLOW.md), skills en [SKILLS.md](SKILLS.md). Git/Markdown son la verdad; Codebase Memory es derivado.

## Entrega

Base `de7abbe`, rama `fix/sales-intent-and-playbooks`. Conversación comercial: consentimiento antes de mutar, cantidades atómicas, selección en la última lista, pedidos compuestos, derivación registrada y tres guías internas del vendedor. Sin migraciones, dependencias ni UI nuevas. [Spec](superpowers/specs/2026-10-27-venta-confiable-y-habilidades-design.md), [plan](superpowers/plans/2026-10-27-venta-confiable-y-habilidades.md) y [reporte](reviews/2026-10-28-venta-confiable.md).

Claude Code implementó el corte inicial; Codex personal revisó y corrigió R1; root coordinó/documentó, aplicó los parches exactos del autor y ejecutó pruebas. **Código y documentación aprobados por Claude en revisión cruzada del snapshot post R3.** [Dictamen](reviews/2026-10-28-venta-confiable-claude.md). Matías autorizó publicar a Git y dejar continuidad para Tomi.

## Evidencia y límites

Root ejecutó **269 passed, 0 failed, 0 skipped**, 62,71s, DB local descartable 55436, migraciones 0001–0007, pagos simulados y planner guionado. Dos warnings históricos: httpx/Starlette y clave JWT corta exclusiva de tests. No hubo cambios de UI, por lo que no se repitió build web.

Playwright + Ollama Cloud `gpt-oss:120b-cloud`: seis mensajes del recorrido real, una sola corrida, 12 llamadas adicionales (42 acumuladas de aceptación). Resultado: un flexible/par $6.800 + una Aquaflux mate $89.900 = **$96.700**, sin productos ajenos. «La nro3» aclara que la lista vigente tiene dos opciones, sin duplicar. T1–T5 live; **T6 mock**, después de rechazar respuesta y reescritura que citaban mal la opción 3. Aceptación funcional cumplida; aceptación íntegramente live incompleta. [Transcripción y captura](reviews/2026-10-28-venta-confiable-ui.md).

Las guías `asesorar_catalogo`, `gestionar_carrito`, `cerrar_o_derivar` orientan al planner; no instalan plugins de desarrollo, conceden permisos ni entrenan al modelo. Hay límites heurísticos del lenguaje y afirmaciones libres que pueden ser inexactas. «Quiero/necesito un X» inequívoco puede agregar al carrito; crear pedido/link conserva confirmación explícita. La derivación registra una oportunidad, sin bandeja completa ni aviso externo.

## Arquitectura y datos

Tomi incorporó perfiles versionados, políticas del servidor, capacidades apagables, memoria/compactación, documentos y evaluaciones en dry-run. [Investigación](research/2026-10-27-arquitectura-agentes-personalizados.md). **0007_agent_architecture.sql existe en Git** y se aplicó localmente; su aplicación remota no se verificó.

No se cambió Supabase remoto ni el `.env` del usuario. Demo de esta PC: Supabase local 54321/54322, Auth local y pagos simulados. Ollama Cloud usa el cliente local autenticado; no convierte la DB en remota. El worker conserva mock para evitar llamadas cloud de fondo. Tests/reset/seed sólo en DB descartable 55436; aceptación aislada 8078/4174. No ejecutar pytest/reset sobre demo ni nube. Los puertos locales no implican que los servicios estén activos en otra PC.

## Continuidad para Tomi

[Pase con mensaje listo para su Claude](handoffs/2026-10-28-tomi-continuidad.md). Puede elegir la siguiente entrega del [roadmap](roadmap.md). Pendientes: calibrar selección/numeración del modelo real y probar otros compradores; bandeja humana; retención/opt-in/vista y borrado de memoria; PDF en documentos; WhatsApp, Mercado Pago real por negocio y logística.

[Comprobantes de clientes](handoffs/2026-10-26-tomi-comprobantes.md): checkpoint OCR en ZIP con hashes, fuera del backend, **no integrado ni aprobado**. Su próxima migración disponible es **0008**. Una imagen/OCR recibido no verifica un pago ni reemplaza su confirmación por proveedor.

Primer producto: catálogo/fotos/precio/stock para comercios que usan Excel/WhatsApp, asesoramiento, pedidos y panel. Sin clientes ni validación comercial registrada; investigación para toda Argentina. Definir fuente principal de inventario antes de mostrador/reportes. Negociación, reposición, diseño y renders son ampliaciones. Carpeta comercial/video anterior en paquete local externo; sin campañas ni contacto público agregado.

## Memoria

El cierre usa [.codebase-memory/artifact.json](../.codebase-memory/artifact.json): consultar ahí revisión/fecha exactas. El commit del artefacto puede ser posterior al commit fuente indexado. Modo fast excluye docs, E2E, migraciones y estáticos; leerlos directamente. No instala skills ni garantiza ahorro de tokens. Tomi puede usar sólo Claude con revisión en contexto fresco, sin las cuentas de Mati.

Historial: [estado previo](state-history-2026-10-27-before-sales-intent.md). Los conteos antiguos no validan este diff.
