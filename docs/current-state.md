# Estado actual — materialIA

**Primera lectura, cierre 27/10/2026.** Invariantes en [CLAUDE.md](../CLAUDE.md), roles/cierre en [AI-WORKFLOW.md](AI-WORKFLOW.md), skills en [SKILLS.md](SKILLS.md). Consultar el detalle sólo según tarea.

## Entrega y próximo paso

El usuario autorizó integrar todo el cierre a `main`. PR #12 ya integrada: privacidad/continuidad del chat público, código `e0e3317`, merge `36cb4cf`. Este corte agrega conversación coherente y conserva OCR como checkpoint. Claude Code implementó; Codex personal revisó; el orquestador coordinó y documentó, sin implementar producto.

**Primera tarea de Tomi:** [comprobantes de clientes](handoffs/2026-10-26-tomi-comprobantes.md). Incluye mensaje listo para su Claude, alcance, diseño, fuentes OCR y revisión pendiente. Resolver primero los cuatro hallazgos del motor y luego integrar registro mensual/constancia. El OCR **no está activo ni aprobado**: fuentes en ZIP con hashes, fuera del backend ejecutable. La migración 0007 todavía no existe.

## Conversación entregada

Respeta estados reales y varios pedidos; cierra agradecimientos sin volver a pedir un pago confirmado; conserva restricciones pertinentes al corregir búsquedas, incluido presupuesto; compara/recomienda desde la ficha y deriva por datos faltantes. Controla precios, stock y acciones/canales; una reescritura sin herramientas evita repetir mutaciones. Mantiene confirmación explícita de compra y elimina la promesa de aviso automático de despacho. Sin WhatsApp/email ni autoaprendizaje.

[Reporte](reviews/2026-10-26-conversacion-natural.md), [aprobación final de Codex](reviews/2026-10-26-conversacion-natural-codex.md) y [hashes revisados](reviews/2026-10-26-conversacion-natural-manifest.json). Mejora acotada para demo: controles heurísticos y recomendaciones austeras con fichas escasas; no garantiza detectar toda afirmación falsa ni parecer humano en cualquier conversación.

## Evidencia

Backend final: **174 aprobadas, 0 fallidas, 0 salteadas**, `PV_REQUIRE_DB=1`, sin exclusiones, Postgres local descartable 0001–0006 y seed sintético. El orquestador repitió el mismo código: 174 aprobadas en 49,37 s. Usuarios/JWT locales de prueba, pagos simulados y planner guionado: no es validación completa de Supabase Auth ni cobros reales. Dos warnings de dependencias/JWT de prueba en el reporte.

Ollama qwen3:8b: 17 llamadas de máximo 20, con timeout/fallos iniciales conservados y comparación factual posterior; 25–132 s/llamada. No representa producción ni evalúa gpt-oss:120b del video. Revisión estática de Codex con fuentes adjuntas, sin comandos por política de su CLI. Implementación claude-opus-5-5, high solicitado sin verificación del esfuerzo efectivo; revisión gpt-6.1-sol/high verificados.

Build y 36 comprobaciones Chrome son evidencia de PR #12, **no se repitieron** en este corte sin cambios de UI/contratos. [Reporte R2](reviews/2026-10-26-chat-publico.md). Estados anteriores: [26/10](state-history-2026-10-26.md) y [R2 antes de este cierre](state-history-2026-10-27-r2.md).

## Nube y límites

Tomi informó el 26/10 **0001–0005 y demo** en remoto; no se verificó independientemente porque el conector rechazó la lectura. No se cambió nube ni `.env`. El chat de PR #12 requiere **0006 antes de usarlo contra el remoto**: verificar versiones y contar con instrucción expresa antes de migrar. Tests/reset/seed usaron sólo DB local descartable; secretos fuera de Git.

Mercado Pago real por negocio, WhatsApp, logística y seguimientos siguen pendientes de integración/validación. Chat con tokens en sessionStorage, sin expiración/revocación; cerrar la pestaña pierde la referencia. No declarar producción lista por estos tests.

## Producto y decisiones abiertas

Primer producto: catálogo/fotos/precio/stock para comercios que usan Excel/WhatsApp, atención/recomendaciones, pedidos y control en panel. Negociación con reglas, intervención humana y reposición requieren entregas propias. Diseño/instalación y renders son ampliaciones. Definir si el panel será inventario principal, incluyendo mostrador, o habrá una fuente sincronizada antes de esos movimientos/reportes.

Sin clientes ni validación comercial registrada. Investigación: toda Argentina. Carpeta comercial/video de la etapa anterior está en un paquete local externo al repo; no se ejecutaron campañas/contactos y no se agregó contacto público por decisión del usuario. Aprendizaje supervisado queda después de comprobantes; no hay autoentrenamiento.

## Continuidad y memoria

Briefs cortos, un owner por archivo, revisión separada y evidencia en archivos según [economía de contexto](AI-WORKFLOW.md#economía-de-contexto). Tomi puede usar sólo Claude Code con revisión en contexto fresco.

Codebase Memory se actualiza al cerrar sobre el commit fuente aprobado; [.codebase-memory/artifact.json](../.codebase-memory/artifact.json) registra revisión/fecha exactas. El commit del artefacto es posterior a la fuente. Modo fast excluye docs, E2E, migraciones y estáticos, incluido el checkpoint OCR: leerlos directamente. La CLI local sustituye al MCP cerrado; copia del mismo commit por compatibilidad Git/WSL. Git/Markdown son la verdad; el índice es derivado, no carga skills ni garantiza ahorro de tokens.
