# Mapa de skills

Seleccionar skills según la fase y leer sus instrucciones en el entorno que ejecuta la tarea. Este mapa permite preparar un entorno compartido; no acredita que el entorno del otro socio ya tenga esas instalaciones, herramientas o permisos.

| Colección | Cuándo aporta | Origen registrado |
|---|---|---|
| Superpowers | Refinar ideas, especificar, planificar, TDD, debugging, revisión y verificación. | [obra/superpowers](https://github.com/obra/superpowers) |
| Agent Skills | Arquitectura, API, implementación incremental, seguridad, frontend, rendimiento, pruebas y entrega. | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) |
| Matt Pocock | Modelado de dominio, módulos, especificaciones, tickets, implementación y revisión. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| Ponytail | Elegir la solución más simple que resuelve el alcance; revisión, auditoría y deuda. | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) |
| Impeccable | Diseño, accesibilidad, responsive, tipografía y pulido de interfaces. | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |
| Taste Skill | Dirección visual, rediseño, estilos y referencias visuales para frontend. | [leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill) |
| Design | Crítica, sistema de diseño, investigación, accesibilidad y UX copy. | Catálogo disponible en el entorno. |
| Engineering | Arquitectura, debugging, documentación, testing, incidentes y despliegues. | Catálogo disponible en el entorno. |
| Locales | Archify para diagramas; Code Review para revisión; Codebase Design y Domain Modeling para diseño; Research, Diagnosing Bugs y Writing for Agents según la tarea. | Kit opcional de variantes locales descrito en [ONBOARDING.md](ONBOARDING.md); verificar procedencia, instalación y activación antes del brief. |
| Supabase | Toda tarea sobre Supabase; sumar buenas prácticas de Postgres cuando cambian consultas o esquema. | Catálogo disponible en el entorno. |

## Referencia de instalación

### Skills de negocio compartidas (09/11/2026)

El proyecto incluye **17 skills completas** en [`.claude/skills/`](../.claude/skills/README.md), con recursos, scripts auxiliares y licencias MIT. [El manifiesto](../.claude/skills/manifest.json) registra origen, revisión contrastada y SHA-256 de cada archivo. Son copias de las que Mati usó con Claude el 09/11; su contenido coincide con los orígenes registrados, normalizando finales de línea.

| Grupo | Skills | Cuándo leerlas |
|---|---|---|
| Founder (11) | `founder-board`, `founder-brand`, `founder-cfo`, `founder-competitors`, `founder-consumer`, `founder-launch`, `founder-marketing`, `founder-offer`, `founder-ops`, `founder-plan`, `founder-pricing` | Evaluación del negocio, propuesta, precio, escenarios, operación y lanzamiento. |
| Startup (4) | `startup-design`, `startup-competitors`, `startup-pitch`, `startup-positioning` | Validación por fases, competencia, posicionamiento y presentación. |
| Marketing (2) | `customer-research`, `sales-enablement` | Entrevistas e investigación de clientes; material comercial. |

En Claude Code, abrir la raíz del repo y comprobar que aparecen las skills del proyecto; las personales homónimas pueden tener prioridad. Codex puede leer estas instrucciones por su ruta cuando la tarea lo requiera; esta ubicación no acredita su descubrimiento automático en Codex. Seguir [ONBOARDING](ONBOARDING.md).

Para continuar el trabajo de negocio, leer primero [founder/README.md](../founder/README.md), [PROGRESS.md](../founder/startup-design/PROGRESS.md) y las correcciones enlazadas. Las simulaciones no reemplazan entrevistas. Respetar `AI-WORKFLOW.md`: brief acotado, presupuesto de contexto y revisión; no ejecutar todos los packs o paneles masivos automáticamente.

### Referencia anterior de herramientas de ingeniería

Verificado en el equipo de origen el **25/10/2026**; no es un requisito de versiones para todos los entornos:

| Colección | Claude Code | Codex orquestador |
|---|---|---|
| Superpowers | 7.0.0, 15 skills | 7.0.0 |
| Agent Skills | 24 skills declaradas | 0.6.13, 25 skills |
| Matt Pocock | 1.3.1, 27 skills declaradas | Copias locales; comprobar exposición en la sesión. |
| Ponytail | 4.10.0 | 5.3.2 |
| Impeccable | 4.3.1, una skill con 24 subcomandos | Comprobar disponibilidad en la sesión. |
| Taste Skill | 1.0.0, 13 skills | Comprobar disponibilidad en la sesión. |

Las diferencias de versión pueden implicar instrucciones distintas: registrar las efectivas en el brief cuando influyan en la entrega. Design, Engineering, skills locales y conectores se verifican en cada entorno. Usar sólo las skills que aporten al trabajo, sin cargar todas las colecciones en cada tarea.

Los seis enlaces públicos identifican el core compartible. La instalación y los comandos concretos de la CLI del socio siguen pendientes de verificación: consultar las instrucciones oficiales del origen y comprobar versión, plugin habilitado y skills expuestas antes de utilizarlos. Design y Engineering requieren confirmar su distribución. El kit local es opcional y se verifica por separado; si coincide un nombre con una skill de un plugin, elegir implementación y versión antes de instalar otra copia. Ver [ONBOARDING.md](ONBOARDING.md).

**Codebase Memory es un MCP**, no una skill ni la fuente de verdad. Su uso y registro están definidos en [AI-WORKFLOW.md](AI-WORKFLOW.md).
