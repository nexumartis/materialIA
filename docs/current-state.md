# Estado actual — materialIA

**Primera lectura, 29/10/2026.** Invariantes en [CLAUDE.md](../CLAUDE.md), roles en [AI-WORKFLOW.md](AI-WORKFLOW.md), skills en [SKILLS.md](SKILLS.md), etapas en [roadmap.md](roadmap.md). Git y Markdown son la verdad; Codebase Memory es derivado y **no** se reindexó en este cierre.

## Entrega: comprobantes de clientes (roadmap etapa 1, hecha)

En `main` con los PRs #16 (T1+T2) y #17 (T3+T4); las correcciones de la revisión van en la rama `fix/comprobantes-revision`. Lo implementó Claude Code en la sesión de Tomi.

- **T1 — OCR local:** RapidOCR/ONNX en CPU, modelos fijados por hash, plazo total de 60 s y red bloqueada por el SO (macOS/Linux).
- **T2 — Pago y constancia:** el dueño confirma la transferencia que cotejó en su banco, con el mismo efecto que un pago del proveedor. Constancia y aviso en la misma transacción. Migración 0008.
- **T3 — Comprobantes:** el comprador sube el comprobante al pedido y el worker lo lee. El panel lista, muestra el original, descarta y confirma asociando comprobantes. CSV mensual en hora argentina. Migración 0009.
- **T4 — PDF y pantallas:** constancia en PDF, chat del comprador y panel del dueño. Aceptación en navegador.

Un archivo o su OCR **nunca** acreditan un pago. Las decisiones y alternativas están en [decisions/2026-10-29](decisions/2026-10-29-comprobantes-implementacion.md); el detalle, en la [revisión](reviews/2026-10-28-comprobantes.md).

## Revisión

T1–T4 entraron a `main` **sin** la revisión cruzada de Mati, porque Tomi mergeó los PRs. Después hubo una revisión de Claude en un contexto separado (`/code-review high` sobre `94f0c26..ba3259a`), que no acredita diversidad de modelo ni de cuenta. Encontró 10 problemas y los 10 se corrigieron en `fix/comprobantes-revision`, cada uno con su test:

- devolver un pago duplicado reintegraba el pedido entero;
- una confirmación con error de tipeo dejaba plata fantasma en el CSV y asociaba los comprobantes;
- una constancia de un pedido reintegrado seguía mostrándose válida (ahora sale ANULADA);
- un PDF con texto y logo se pasaba igual por OCR;
- subir el mismo archivo a la vez en dos pedidos daba 500;
- el panel no aceptaba importes con formato argentino;
- el OCR podía frenar el worker;
- `CLAUDE.md` no contemplaba las transferencias verificadas por el dueño;
- había lógica duplicada.

**Pendiente:** revisión de Mati con Codex sobre todo el conjunto.

## Evidencia (29/10/2026, macOS, Python 3.14)

- **Backend:** **325 passed, 0 failed, 0 skipped** en una DB descartable (`127.0.0.1:55436`, contenedor `materialia-test-pg`, 0001–0009 + seed). Warnings históricos: httpx/Starlette y JWT corto de tests.
- **Navegador** (entorno aislado: API 8078, web 4174, worker, LLM `mock`, pagos simulados):
  - `npm run e2e:comprobantes`: **17/17**;
  - `npm run e2e`: **36 PASS, 0 FAIL**.
- **Control visual:** PDF de la constancia y panel de pedidos.

## Datos y entornos

- **Supabase remoto** (`zfmjcturyhxytyfzmcha`): según `supabase migration list --linked` del 29/10, tiene 0001–0005 y le faltan **0006–0010**. 0006 (privacidad del chat) ya estaba pendiente antes de este corte. Si la app corre contra la nube con el código actual, los pagos y comprobantes fallan. Aplicar requiere instrucción expresa.
- **Demo local de esta PC:** Supabase 54321/54322 con 0001–0010 (0004–0007 se registraron porque las tablas ya existían; sin reset), API 8077 y web 5173. El worker no corre solo: `python -m app.worker`.
- **Antes de un piloto real:**
  - almacenamiento privado para los originales (hoy `bytea`) y una política de retención;
  - comprobantes de bancos argentinos reales;
  - decidir si, sin aislamiento de red del SO (Windows), el OCR debe negarse a leer.

## Entrega en curso: bandeja y toma de control humana (roadmap etapa 2)

Rama `feat/bandeja-humana`; [spec](superpowers/specs/2026-10-29-bandeja-humana-design.md) y [revisión](reviews/2026-10-29-bandeja.md). Tomi pidió avanzar sin ronda de preguntas, así que lo marcado como «decisión de Claude» en la spec está pendiente de acuerdo entre los socios.

- **Panel:** página Conversaciones con filtros (derivadas, sin responder, mías, con pedido, todas), y acciones para tomar el control, responder como persona y devolver al asistente.
- **Agente:** si la conversación está tomada, no responde, ni siquiera cuando se la toman a mitad de un turno. Los mensajes de una persona no entran al historial del modelo.
- **Comprador:** ve «Equipo de <negocio>» y el aviso «Te está atendiendo una persona del negocio».
- **Migración 0010:** el panel lee conversaciones por columnas, sin `access_token_hash` ni `agent_state`. Además: `needs_human_reason` (`asked`/`quote`) y la toma de control.
- **Revisión** `/code-review high` en contexto fresco: 10 hallazgos, todos corregidos con test.
- **Evidencia (29/10):**
  - backend **339 passed**;
  - `e2e:bandeja` **11/11** (dos corridas), `e2e:comprobantes` **17/17**, `e2e` **36 PASS, 0 FAIL**.
- **Fuera del corte:** sugerencias del agente al humano y notificaciones.

**Entorno:** las corridas completas de pytest tardan a veces más de 10 minutos de reloj, aunque pytest mide 22–42 s; un volcado de `faulthandler` no mostró ningún test colgado. Además, un `python -m app.worker` que queda corriendo contra la base de pytest compite con los tests: frenarlo al terminar un e2e (`pkill -f app.worker`).

## Próximo paso

Revisión de Mati de los PRs de comprobantes y de la bandeja. Después, según el [roadmap](roadmap.md): etapa 6 (asistente paso a paso, front) en paralelo, o etapa 3 (WhatsApp, que requiere cambiar el alcance en CLAUDE.md con ambos socios). Aplicar 0006–0010 en la nube requiere instrucción expresa.

Historial: [estado previo](state-history-2026-10-28-before-comprobantes.md). Los conteos antiguos no validan este diff.
