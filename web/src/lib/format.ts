import type { Opportunity, Requirements, Stage } from "./api";

export const STAGES: { key: Stage; label: string }[] = [
  { key: "nueva", label: "Nueva" },
  { key: "datos_incompletos", label: "Datos incompletos" },
  { key: "para_cotizar", label: "Para cotizar" },
  { key: "cotizada", label: "Cotizada" },
  { key: "seguimiento", label: "Seguimiento" },
  { key: "cerrada", label: "Cerrada" },
];

export const STAGE_LABEL: Record<string, string> = Object.fromEntries(
  STAGES.map((s) => [s.key, s.label]),
);

const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

export function dateOnly(iso: string | null): string {
  return iso ? String(iso).slice(0, 10) : "";
}

export function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-AR", {
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function fmtAmount(n: number | null): string {
  if (n == null) return "—";
  return n.toLocaleString("es-AR");
}

export function isOverdue(o: Opportunity): boolean {
  if (!o.next_action_at || o.stage === "cerrada") return false;
  const d = new Date(dateOnly(o.next_action_at) + "T23:59:59");
  return d < new Date();
}

export function pedidoText(req: Requirements | undefined): {
  main: string;
  sub: string;
} {
  if (!req || !Object.keys(req).length)
    return { main: "Consulta general", sub: "" };
  // Oportunidad del agente de ventas: productos del pedido y su número.
  if (Array.isArray(req.productos) || req.pedido != null || req.producto) {
    const items = Array.isArray(req.productos) ? (req.productos as string[]).join(", ") : String(req.producto ?? "");
    return { main: items || "Pedido", sub: req.pedido != null ? `Pedido #${req.pedido}` : "" };
  }
  const cat = (req.category as string) || "pedido";
  const tc = [req.tipo, req.color].filter(Boolean).join(" ");
  const med =
    req.ancho_mm && req.alto_mm ? `${req.ancho_mm}×${req.alto_mm} mm` : "";
  const extra = [req.localidad, req.customer_name].filter(Boolean).join(" · ");
  return {
    main: `${cap(cat)} ${tc}`.trim(),
    sub: [med, extra].filter(Boolean).join(" · "),
  };
}

/** Importe como lo muestra el banco: "12.345,50", "12345,5" o "12345.50". NaN si no es un número. */
export function parseAmount(text: string): number {
  const t = text.trim().replace(/\s|\$/g, "");
  // Con coma, la coma es el decimal; sin coma, "6.800" (grupos de 3) son miles, no decimales.
  const normalized = t.includes(",") || /^\d{1,3}(\.\d{3})+$/.test(t) ? t.replace(/\./g, "").replace(",", ".") : t;
  return /^\d+(\.\d{1,2})?$/.test(normalized) ? Number(normalized) : NaN;
}
