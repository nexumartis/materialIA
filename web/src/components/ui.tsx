/** Piezas del sistema de diseño compartidas por las pantallas del panel. Los estilos viven en
 *  app.css (tokens + clases); estos componentes sólo fijan la estructura y la accesibilidad. */
import type { ReactNode } from "react";
import { Inbox, X, type LucideIcon } from "lucide-react";

export function PageHeader({ title, description, actions }: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="titlebar">
      <div>
        <h1>{title}</h1>
        {description && <p className="finding">{description}</p>}
      </div>
      {actions && <div className="right">{actions}</div>}
    </div>
  );
}

export interface Stat {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "neg";
}

/** Franja de métricas con divisores (una sola tarjeta, como en un dashboard SaaS). */
export function Stats({ items, label }: { items: Stat[]; label: string }) {
  return (
    <section className="kpis" aria-label={label}>
      {items.map((s) => (
        <div className="kpi" key={s.label}>
          <div className="l">{s.label}</div>
          <div className={`n${s.tone === "neg" ? " neg" : ""}`}>{s.value}</div>
          {s.hint && <div className="sub">{s.hint}</div>}
        </div>
      ))}
    </section>
  );
}

export type BadgeTone = "pos" | "neg" | "warn" | "neu" | "info";

export function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

export function EmptyState({ icon: Icon = Inbox, title, children }: {
  icon?: LucideIcon;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-box" role="status">
      <Icon size={20} strokeWidth={1.6} aria-hidden />
      <b className="empty-title">{title}</b>
      {children && <span>{children}</span>}
    </div>
  );
}

/** Barra flotante de acciones al seleccionar filas de una tabla. */
export function SelectionBar({ count, onClear, children }: {
  count: number;
  onClear: () => void;
  children: ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div className="selection-bar" role="toolbar" aria-label="Acciones sobre la selección">
      <span className="count" aria-live="polite">{count} {count === 1 ? "seleccionado" : "seleccionados"}</span>
      {children}
      <button className="btn sm icon" type="button" onClick={onClear} aria-label="Quitar selección">
        <X size={15} strokeWidth={1.8} aria-hidden />
      </button>
    </div>
  );
}
