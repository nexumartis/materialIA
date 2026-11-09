# Estado actual — materialIA

**Actualizado: 09/11/2026.** Primera lectura para ambos socios y sus agentes.
Invariantes en [CLAUDE.md](../CLAUDE.md), roles en [AI-WORKFLOW.md](AI-WORKFLOW.md).

## Base técnica comprobada

Main remoto consultado: **`b8714faaecc1ac1bd49791acef60553b157bd437`**,
merge del [PR #74](https://github.com/nexumartis/materialIA/pull/74), el 08/11/2026.
Esta entrega documental parte de esa revisión. Incluye los cambios previos de Tomi y Mati:

- Cuentas, negocios, roles y aislamiento; agente con catálogo real, stock, carrito, pedidos,
  pagos verificados, comprobantes/OCR, bandeja humana y panel.
- Audio web con ElevenLabs (PR #67), reparto/agenda/franjas/correo (PRs #68–70),
  fotos para buscar en el catálogo (PR #71) y documentos founder (PR #72).
- WhatsApp oficial, etapa 1 (PR #74): conexión por negocio, token cifrado, firma del webhook,
  texto entrante/saliente, idempotencia, cola/reintentos, ventana de 24 horas y respuesta desde
  la bandeja. No confundir con campañas, audio de WhatsApp, Instagram o alta SaaS integrada.
- El esquema versionado llega a **0034_whatsapp.sql**. Esto no certifica qué migraciones
  tiene hoy una DB local o remota; no se inspeccionaron ni modificaron bases en esta entrega.

La prueba real de WhatsApp está pendiente según [whatsapp-pruebas.md](whatsapp-pruebas.md):
se registró `Business account locked` entre el 08 y el 09/11. No se verificó de nuevo la cuenta.
ElevenLabs requiere secretos y configuración de cada entorno; no se consumieron créditos aquí.
Consultar [audio-web.md](audio-web.md), distinguiendo su handoff inicial del código ya integrado.

## Trabajo de negocio de hoy, compartido

Empezar por [founder/README.md](../founder/README.md). Se incorporan los **24 archivos**
producidos con Claude el 09/11: intake, brainstorm, investigación/síntesis, insumos,
verificación, compuerta, progreso y guía/planilla de entrevistas.

- Orientación para validar: sanitarios/grifería de CABA, instalación acompañada y precio
  tentativo de $70.000. No hay precio final, demanda validada ni clientes pagos acreditados.
- La planilla de entrevistas contiene sólo encabezados. Segundas visitas y aceptación de
  un piloto/precio deben registrarse por separado de la primera charla de investigación.
- El análisis del 05/11 ($35.000, varios rubros y GBA sur) queda identificado como antecedente;
  no tomar sus cronogramas, garantías ni cifras como acuerdos vigentes.
- Se corrigió el supuesto de cobro de respuestas de servicio de Meta: ver
  [correcciones del 09/11](../founder/startup-design/01-discovery/corrections-2026-11-09.md).
  Los insumos originales y la verificación anterior se conservan con advertencias.

## Skills y forma de trabajar

Las **17 skills de negocio completas** viven en [`.claude/skills/`](../.claude/skills/README.md),
con referencias, scripts, licencias MIT y [manifiesto de integridad](../.claude/skills/manifest.json).
Tomi puede abrir el repo con su propio Claude Code y comprobar su carga. Para ingeniería,
ver [SKILLS.md](SKILLS.md). Las cuentas, plugins personales y `.env` no se comparten.

El orquestador coordina y documenta; Claude Code y Codex personal implementan y revisan
cruzadamente cuando se usa esa modalidad. Tomi puede usar Claude con revisión en otro contexto.
Mantener briefs cortos, un owner por archivo y cargar sólo lo necesario para cada tarea.

## Evidencia y límites de este cierre

Esta entrega es documental y de distribución de skills: no modifica producto ni migraciones.
Se comprueban integridad/procedencia de skills, sintaxis de los datos y enlaces de la entrega,
diff, archivos publicables y revisión independiente; el resultado queda en
[la revisión](reviews/2026-11-09-continuidad-founder.md).

La cifra **622 tests** fue reportada en el brief de Claude, no reproducida aquí. No se ejecuta
la suite del producto ni se afirma funcionamiento con Meta/ElevenLabs reales por estos cambios.
El [estado del 29/10](current-state-2026-10-29.md) conserva la evidencia histórica de entonces.

## Próximo paso

Ambos socios revisan la orientación comercial y los pendientes del
[progreso guardado](../founder/startup-design/PROGRESS.md). Preparar las primeras charlas con
dueños y una segunda visita con su catálogo. En paralelo, comprobar y resolver el acceso de
Meta para la demo oficial antes de prometer un piloto conectado.

Para retomar con el Claude de Tomi: [ONBOARDING](ONBOARDING.md), con un prompt listo.

## Codebase Memory

Git y estos Markdown son la fuente de verdad. El grafo es un índice derivado del código,
no una memoria de entrevistas o de la conversación. Comprobar su revisión en
[artifact.json](../.codebase-memory/artifact.json) antes de consultarlo. El estado de la
actualización de este cierre se registra en la revisión documental; no asumir que el índice
incluye el commit que publica su propio manifiesto.

**Regenerado el 09/11/2026**, modo `fast`, sobre `0ee50dee6ece2676957014a236aebb9b859e9c00`:
4.231 nodos y 18.120 relaciones; grafo comprimido y manifiesto persistidos. El indexador excluye
`docs/`, `.claude/` y migraciones SQL, entre otros directorios: leer esos archivos directamente.
El commit que comparte este artefacto y esta nota es posterior a la revisión indexada.
