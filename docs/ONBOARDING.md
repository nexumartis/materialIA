# Incorporar el entorno de un socio

El repositorio contiene el acuerdo compartido, el estado, las decisiones y el plan recibido. El socio puede trabajar con su propio Claude Code; la modalidad de revisión está en [AI-WORKFLOW.md](AI-WORKFLOW.md).

## Primera tarea

1. Obtener la revisión compartida del repositorio y leer [current-state.md](current-state.md) y las [invariantes de CLAUDE.md](../CLAUDE.md#reglas-innegociables-no-romper).
2. Confirmar que Claude carga `CLAUDE.md` y sigue [AGENTS.md](../AGENTS.md). Verificar la modalidad, el modelo y esfuerzo efectivos, las herramientas disponibles y el owner/revisor por archivos antes de editar.
3. Elegir del [mapa de skills](SKILLS.md) sólo las skills necesarias para la fase. Confirmar su exposición real en la sesión; el repositorio no las instala.
4. Preparar un brief acotado y trabajar con validación y revisión en contexto separado. Para la próxima entrega de cuentas, empezar por la [decisión de alcance](decisions/2026-10-25-cuentas-alcance.md); el plan original todavía requiere revisión técnica.

## Skills y herramientas del equipo

El core tiene orígenes públicos enlazados en `SKILLS.md`: Superpowers, Agent Skills, Matt Pocock, Ponytail, Impeccable y Taste Skill. La instalación en la CLI del socio sigue pendiente de verificación. Usar las instrucciones oficiales de cada origen y comprobar compatibilidad, versión, habilitación y skills expuestas. No hay comandos de instalación comprobados para su equipo en esta entrega.

Design y Engineering requieren confirmar su distribución. Para variantes locales se preparó, fuera del repositorio, el paquete opcional `materialIA-kit-skills-locales-2026-10-25.zip`, con **12 skills**: Archify, Code Review, Codebase Design, Diagnosing Bugs, Domain Modeling, Grilling, Prototype, Research, Resolving Merge Conflicts, TDD, Wizard y Writing for Agents. Contiene 193 archivos y un README con instalación, checksums y licencias/procedencia. Es un extra local para pasar por fuera de GitHub; comprobar ese contenido y verificar instalación y activación en el Claude del socio antes de usarlo.

La [documentación oficial de skills de Claude Code](https://code.claude.com/docs/en/skills) distingue skills personales en `~/.claude/skills/` y del proyecto en `.claude/skills/`. Para este kit opcional, usar la ubicación personal del socio y conservar los recursos y subdirectorios completos de cada skill. Seguir el README del kit y las instrucciones oficiales para verificar su activación; la presencia de una carpeta no acredita que la sesión la haya cargado.

Si un plugin ya aporta una skill del mismo nombre, elegir la implementación y versión que se utilizará antes de instalar una copia local. Instalar sólo lo necesario para la tarea y evitar duplicaciones; el inventario amplio es una referencia privada y opcional, no una lista para instalar completa.

Codebase Memory es un MCP opcional cuyo [origen oficial es DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp). La indexación y las consultas no necesitan otra cuenta de IA. Requiere instalación y configuración en el equipo del socio; después de clonar, `index_repository` puede aprovechar el artefacto incluido como base cuando la versión y el formato son compatibles. Verificar el contrato exacto de esa herramienta en la versión instalada y la revisión de [artifact.json](../.codebase-memory/artifact.json) antes de usarlo.

Su grafo facilita consultas de código; no crea automáticamente el resumen de negocio, no obliga a leer los Markdown y no garantiza un ahorro fijo de contexto. Con o sin MCP, Git, `current-state.md` y las decisiones permiten retomar el trabajo.

## Qué se comparte y qué queda en cada entorno

| Material | Tratamiento |
|---|---|
| [AGENTS.md](../AGENTS.md), [CLAUDE.md](../CLAUDE.md), [workflow](AI-WORKFLOW.md), [mapa de skills](SKILLS.md), [estado](current-state.md) y esta guía | Preparados para la entrega documental en GitHub. |
| [Decisión de cuentas](decisions/2026-10-25-cuentas-alcance.md) y [plan original](superpowers/plans/2026-10-25-cuentas-multitenant.md) | Preparados para GitHub; el alcance de producto está aprobado y el plan sigue pendiente de aprobación técnica. |
| [Manifiesto](../.codebase-memory/artifact.json) y [grafo](../.codebase-memory/graph.db.zst) de Codebase Memory | Se incluyen en GitHub tras verificar su persistencia y la revisión indexada; la publicación de esta entrega está autorizada. |
| Plugins y skills instalados | Se instalan y verifican en el equipo del socio; los enlaces de origen no acreditan instalación. |
| `materialIA-kit-skills-locales-2026-10-25.zip` | Extra opcional preparado para pasar por fuera de GitHub: 12 skills, 193 archivos; verificar contenido y activación antes de usarlo. |
| Inventario amplio de skills | Referencia privada y opcional; no hace falta enviarlo ni instalar todo para trabajar en el proyecto. |
| Sesiones, perfil del navegador, cuentas, `.env`, secretos y configuraciones privadas | Permanecen en cada entorno. Cada socio usa su acceso autorizado y configura los secretos por el mecanismo local correspondiente. |

## Prompt inicial para Claude Code

```text
Trabajamos en materialIA. Primero leé docs/current-state.md y las reglas
innegociables de CLAUDE.md. Seguí AGENTS.md y docs/AI-WORKFLOW.md.
Usamos la modalidad del socio con Claude Code. Confirmá las instrucciones
cargadas, el modelo/esfuerzo efectivos, las herramientas y las skills
disponibles; consultá docs/SKILLS.md sólo según la fase de la tarea.

Antes de editar, prepará un brief con alcance, archivos, owner y revisor,
criterios de aceptación y validación. Revisá en otra sesión o con un
subagente de sólo lectura y contexto fresco; esa separación no acredita
diversidad de modelo/cuenta. Si no está disponible, prepará diff y evidencia
para el otro socio y dejá la revisión pendiente; avanzá tareas independientes.

La próxima entrega empieza por docs/decisions/2026-10-25-cuentas-alcance.md.
El plan recibido todavía no tiene aprobación técnica: contrastalo antes de
proponer ejecución, incluyendo su referencia de diseño aún no localizada.
Al cerrar, actualizá el estado, revisá, publicá sólo lo autorizado y seguí
el protocolo del índice opcional de Codebase Memory.
```

## Cierre y continuidad

Aplicar el [protocolo de cierre](AI-WORKFLOW.md#protocolo-de-cierre): actualizar estado → revisión → commit autorizado → indexación y persistencia de Codebase Memory si se usa → versionado del artefacto cuando esté autorizado. Registrar errores o herramientas ausentes en los Markdown y conservar la revisión indexada en `artifact.json`.

Esta entrega está lista para revisión final y publicación autorizada mediante una rama y una PR de documentación. La apertura de la PR no autoriza su merge; el resultado de publicación se informa al cierre.
