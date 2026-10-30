# Sistema de diseño del panel

Rediseño del 29/10/2026 a partir de la referencia `CRM_DESIGN.png`: dashboard SaaS minimalista, al estilo de Linear o Stripe. **Fuente única:** los tokens en `:root` de `web/src/styles/app.css`. No usar colores ni medidas sueltas en los componentes.

## Tokens

| Uso | Token | Valor |
|---|---|---|
| Fondo de la app | `--chrome` | `#f7f8fa` |
| Sidebar, hoja, cards | `--surface` | `#ffffff` |
| Encabezados de tabla, hover | `--ground` | `#f8f9fb` |
| Bordes | `--border` / `--rule` | `#e9ebef` / `#eef0f3` |
| Texto principal / secundario | `--text` / `--muted` | `#202124` / `#6b7280` |
| Acción primaria (botón) | `--primary` | `#1b1c1f` |
| Acento (activo, selección, foco, interruptores) | `--accent` | `#ea6a2a` |
| Texto en naranja | `--accent-ink` | `#b03f0e` |
| Fila seleccionada | `--accent-soft` | `#fff4ee` |

- **Badges** (`.pill pos|neg|warn|neu|info`): fondo pastel y texto oscuro, de 11px, con radio de 5px.
- **Tipografía:** Inter. Título 20px, sección 15px, texto 13px, etiquetas 11–12px, métricas 24px.
- **Medidas:** espaciado en múltiplos de 4. Controles de 34px (`.btn.sm` 30px), filas de tabla de 40px, radios de 10 (hoja), 8 (card), 6 (control) y 5 (badge).

**Accesibilidad.** El gris secundario (`#8A8F98`) y los textos de los badges de la referencia se oscurecieron apenas para cumplir WCAG AA (4,5:1). El naranja `#ea6a2a` se usa sólo en indicadores, nunca como texto ni como fondo de un botón con texto blanco.

## Componentes

- **CSS** (`app.css`): `.btn` (`primary`, `ghost`, `sm`, `icon`), `.field`, `.field-select`, `.tablewrap` + `table` (con `th.check`, `tr.selected`, `td.num`, `.row-actions`), `.kpis`/`.kpi`, `.pill`, `.chip[aria-pressed]`, `.empty-box`, `.skel-row`, `.selection-bar`.
- **React** (`web/src/components/ui.tsx`): `PageHeader`, `Stats`, `Badge`, `EmptyState` y `SelectionBar`.
- **Íconos:** sólo Lucide (`lucide-react`, versión fija), outline, de 15–16px, con `strokeWidth` 1.8 y `aria-hidden`.
- **Tablas en celular:** con la clase `stack` se apilan como tarjetas por debajo de 760px. Cada `td` lleva `data-label`. Las tablas con campos editables (Catálogo) se desplazan dentro de su recuadro.

## Navegación

Sidebar en grupos: **Ventas** (Conversaciones, Oportunidades, Pedidos), **Tu agente** (Mi agente → asistente, Ajustes del agente, Catálogo) y **Herramientas** (Demo, API). El ítem activo lleva fondo, borde y una barra naranja. En celular, el sidebar se abre como panel lateral.

## Fuera de este corte

La referencia incluye búsqueda ⌘K, paginación, toasts, tooltips y columnas configurables. No se agregaron porque no hay una funcionalidad detrás.
