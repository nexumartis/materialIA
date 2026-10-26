# Acuerdo de trabajo — materialIA

**Primera lectura en cada tarea:** [estado actual](docs/current-state.md) e [invariantes de negocio y seguridad](CLAUDE.md#reglas-innegociables-no-romper). Confirmá la revisión de código y las observaciones que siguen vigentes antes de decidir el próximo paso.

## Según la tarea

- **Planificar, implementar, revisar o entregar:** seguí [AI-WORKFLOW](docs/AI-WORKFLOW.md), que define modalidades, ownership, revisión y cierre.
- **Elegir skills:** consultá el [mapa de skills](docs/SKILLS.md) y leé sólo las instrucciones pertinentes a la fase.
- **Incorporar el entorno de un socio:** seguí [ONBOARDING](docs/ONBOARDING.md), que incluye un arranque para Claude Code.

## Acuerdo vigente

- Los dos socios acuerdan producto, prioridades, alcance y aceptación final.
- En la modalidad coordinada, el Codex orquestador ayuda a pensar, documenta y coordina; Claude Code y Codex personal implementan con revisión cruzada. El socio que sólo dispone de Claude Code puede planificar e implementar entregas acotadas con revisión en un contexto fresco, según el workflow.
- Cada archivo tiene un único owner durante una entrega y un revisor identificado. La revisión necesita un contexto separado del implementador; registrar la modalidad y sus límites.
- El brief identifica modalidad, ejecutor, owner y revisor por archivos, alcance, skills, modelo y esfuerzo efectivos, validación y criterio de aceptación. Las herramientas y las skills disponibles dependen de cada entorno.
- Las acciones externas y los commits, push, merge y despliegues requieren una instrucción expresa que cubra la acción. El catálogo de herramientas y skills no otorga autorización.

## Continuidad

Al cerrar una entrega, actualizá [docs/current-state.md](docs/current-state.md), revisá el resultado y seguí el protocolo de publicación e indexación del workflow. Git y los Markdown conservan la verdad del proyecto; Codebase Memory es un índice derivado opcional.
