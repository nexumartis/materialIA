# Diagramas de Presupuesto Vivo

Diagramas interactivos (HTML standalone, generados con [Archify]). Se abren directo en el
navegador (`file://`), con tema claro/oscuro, animación y exportación.

- **Ciclo de vida de una oportunidad** — [`ciclo-de-vida-oportunidad.html`](./ciclo-de-vida-oportunidad.html)
  Etapas (`nueva → para_cotizar → cotizada → seguimiento → cerrada`), la pausa por datos
  incompletos, y las reglas: cada transición va al timeline y cerrar limpia el seguimiento.

El `.json` junto a cada `.html` es el candidato fuente. Para regenerar:

```bash
node <ruta-archify>/bin/archify.mjs finalize <sequence|lifecycle> \
  docs/diagramas/<nombre>.json docs/diagramas/<nombre>.html --quality showcase
```
