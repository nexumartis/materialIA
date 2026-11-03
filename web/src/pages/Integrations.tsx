import { useCallback, useEffect, useState } from "react";
import { Copy, Landmark, MapPin, MessageSquareCode, PlugZap, Trash2, Webhook, X, type LucideIcon } from "lucide-react";
import { siGooglecalendar, siGooglesheets, siInstagram, siMake, siMercadopago, siShopify, siWhatsapp, siWoocommerce,
  siZapier, type SimpleIcon } from "simple-icons";
import { SheetSync } from "../components/SheetSync";
import { Badge, EmptyState, PageHeader } from "../components/ui";
import { api, type Health, type Webhooks } from "../lib/api";

const EVENT_LABEL: Record<string, string> = {
  "order.paid": "Pedido pagado",
  "order.deposit_paid": "Seña cobrada",
  "order.cancelled": "Pedido cancelado",
  "conversation.needs_human": "Conversación derivada a una persona",
  "order.rated": "Pedido calificado",
};
const when = (iso: string) => new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });

/** Webhooks: el negocio recibe eventos firmados en su sistema (planilla, ERP, CRM, Zapier/Make). */
function WebhooksPanel({ onChange }: { onChange?: () => void }) {
  const [data, setData] = useState<Webhooks | null>(null);
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<string[]>([]);
  const [secret, setSecret] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.webhooks().then((d) => { setData(d); setEvents((e) => (e.length ? e : d.events)); },
      (e) => setError(e instanceof Error ? e.message : "No pude cargar las integraciones."));
  }, []);
  useEffect(load, [load]);

  async function run<T>(action: () => Promise<T>, done?: (r: T) => void) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const r = await action();
      done?.(r);
      load();
      onChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <form className="team-invite" onSubmit={(e) => {
        e.preventDefault();
        void run(() => api.createWebhook(url.trim(), events), (r) => { setSecret(r.secret); setUrl(""); });
      }}>
        <label htmlFor="wh-url">URL de tu endpoint (https)</label>
        <div className="row">
          <input id="wh-url" type="url" required placeholder="https://hooks.zapier.com/..." value={url}
            onChange={(e) => setUrl(e.target.value)} />
          <button className="btn primary" type="submit" disabled={busy || !url.trim() || !events.length}>
            <PlugZap size={15} strokeWidth={1.8} aria-hidden /> Conectar
          </button>
        </div>
        {data && (
          <fieldset className="wh-events">
            <legend className="small">Eventos</legend>
            {data.events.map((ev) => (
              <label key={ev} className="small">
                <input type="checkbox" checked={events.includes(ev)}
                  onChange={(e) => setEvents((list) => e.target.checked ? [...list, ev] : list.filter((x) => x !== ev))} />{" "}
                {EVENT_LABEL[ev] ?? ev}
              </label>
            ))}
          </fieldset>
        )}
      </form>
      {secret && (
        <div className="results-callout" role="status">
          <b>Guardá este secreto ahora: no se vuelve a mostrar.</b> Con él verificás la firma <code>X-PV-Signature</code>.
          <div className="wh-secret"><code>{secret}</code>
            <button className="btn sm" type="button" onClick={() => void navigator.clipboard?.writeText(secret).then(() => setNote("Secreto copiado."))}>
              <Copy size={14} strokeWidth={1.8} aria-hidden /> Copiar
            </button>
            <button className="btn sm ghost" type="button" onClick={() => setSecret(null)}>Ya lo guardé</button>
          </div>
        </div>
      )}
      {note && <p className="muted small" role="status">{note}</p>}
      {error && <p className="state err" role="alert">{error}</p>}

      {!data ? (!error && <div className="state">Cargando…</div>) : data.endpoints.length === 0 ? (
        <EmptyState icon={PlugZap} title="Todavía no conectaste ningún sistema">
          Pegá la URL que te da tu herramienta (por ejemplo, un «Catch Hook» de Zapier) y elegí qué eventos querés recibir.
        </EmptyState>
      ) : (
        <ul className="team-list" aria-label="Endpoints">
          {data.endpoints.map((ep) => (
            <li key={ep.id}>
              <span className="who" title={ep.url}>{ep.url}<br />
                <small className="muted">{ep.events.map((e) => EVENT_LABEL[e] ?? e).join(" · ")}</small>
              </span>
              {ep.last_error ? <Badge tone="neg">Falló: {ep.last_error}</Badge>
                : ep.last_success_at ? <Badge tone="pos">Último envío {when(ep.last_success_at)}</Badge>
                : <Badge tone="neu">Sin envíos</Badge>}
              <button className="btn sm" type="button" disabled={busy}
                onClick={() => void run(() => api.testWebhook(ep.id), (r) => setNote(r.ok ? "Prueba enviada: respondió bien." : `La prueba falló: ${r.error ?? r.status_code}`))}>
                Probar
              </button>
              <button className="btn sm ghost" type="button" aria-label="Quitar endpoint" disabled={busy}
                onClick={() => window.confirm("¿Quitar este endpoint? Deja de recibir eventos.") && void run(() => api.deleteWebhook(ep.id))}>
                <Trash2 size={14} strokeWidth={1.8} aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
      {data && data.deliveries.length > 0 && (
        <section className="results-card" aria-labelledby="wh-log">
          <h2 id="wh-log">Últimos envíos</h2>
          <table className="results-table">
            <thead><tr><th>Evento</th><th>Estado</th><th className="num">Intentos</th><th>Fecha</th></tr></thead>
            <tbody>{data.deliveries.map((d) => (
              <tr key={d.id}>
                <td>{EVENT_LABEL[d.event] ?? d.event}</td>
                <td>{d.status === "sent" ? "Entregado" : d.status === "failed" ? `Falló${d.last_error ? `: ${d.last_error}` : ""}` : "Pendiente"}</td>
                <td className="num">{d.attempts}</td>
                <td>{when(d.created_at)}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      )}
      <details className="results-table-toggle">
        <summary>Cómo verificar la firma</summary>
        <p className="small">Cada envío trae <code>X-PV-Signature: t=&lt;unix&gt;,v1=&lt;hex&gt;</code>. Calculá
          HMAC-SHA256 con tu secreto sobre <code>&lt;t&gt;.&lt;cuerpo crudo&gt;</code>, compará con <code>v1</code> y descartá
          envíos con <code>t</code> de más de 5 minutos. <code>X-PV-Delivery</code> es único: usalo para no procesar dos veces.
          Si tu servidor no responde 2xx, reintentamos a los 1, 5 y 30 minutos, 2 y 6 horas.</p>
      </details>
    </div>
  );
}

/** Código para pegar el chat de la tienda en la web del comercio (botón flotante + ventana). */
export function WebChatSnippet() {
  const [slug, setSlug] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { api.agentProfile().then((p) => setSlug(p.public_slug ?? null), () => setSlug(null)); }, []);
  if (!slug) return null;
  const code = `<script src="${window.location.origin}/widget.js" data-tienda="${slug}" async></script>`;
  return (
    <section className="results-card" aria-labelledby="webchat-title">
      <h2 id="webchat-title">Chat para tu página web</h2>
      <p className="muted small">
        Pegá este código antes de <code>&lt;/body&gt;</code> en tu web (o en el «HTML personalizado» de tu plataforma). Aparece un
        botón «¿Te ayudo?» que abre tu asistente, con tu catálogo, carrito y cobro verificado. Opcional: <code>data-color="#1b1c1f"</code>.
      </p>
      <div className="wh-secret"><code>{code}</code>
        <button className="btn sm" type="button" onClick={() => void navigator.clipboard?.writeText(code).then(() => setCopied(true))}>
          <Copy size={14} strokeWidth={1.8} aria-hidden /> {copied ? "Copiado" : "Copiar"}
        </button>
        <a className="btn sm ghost" href={`#/tienda/${slug}`} target="_blank" rel="noopener noreferrer">Ver la tienda</a>
      </div>
    </section>
  );
}

// --- Catálogo de integraciones ---------------------------------------------------------
type Status = "on" | "available" | "soon";
type Category = "pagos" | "catalogo" | "automatizacion" | "canales" | "operacion";
interface Item {
  key: string; name: string; category: Category; blurb: string;
  logo: SimpleIcon | { mono: string; color: string; ink?: string } | LucideIcon;
  status: (s: Ctx) => Status; statusText?: (s: Ctx) => string;
  detail?: (s: Ctx) => React.ReactNode;
}
interface Ctx { health: Health | null; sheet: boolean; webhooks: number; reload: () => void }

const CATEGORIES: { key: Category | "todas"; label: string }[] = [
  { key: "todas", label: "Todas" }, { key: "pagos", label: "Pagos" }, { key: "catalogo", label: "Catálogo" },
  { key: "automatizacion", label: "Automatización" }, { key: "canales", label: "Canales" }, { key: "operacion", label: "Operación" },
];

const steps = (lines: string[]) => <ol className="intg-steps">{lines.map((l) => <li key={l}>{l}</li>)}</ol>;

const ITEMS: Item[] = [
  { key: "mercadopago", name: "Mercado Pago", category: "pagos", logo: siMercadopago,
    blurb: "Link de pago en el chat. El pedido figura pagado sólo con el aviso verificado de Mercado Pago.",
    status: (c) => (c.health?.payments?.provider === "mercadopago" ? "on" : "available"),
    statusText: (c) => (c.health?.payments?.provider === "mercadopago" ? "Conectada" : "Modo prueba"),
    detail: (c) => (c.health?.payments?.provider === "mercadopago"
      ? <p>Cobros reales activos. Cada pago se consulta a Mercado Pago antes de marcar el pedido como pagado.</p>
      : <p>Hoy los pagos son <b>simulados</b> (no se cobra nada). Para cobrar de verdad, el equipo técnico carga las credenciales de Mercado Pago del negocio.</p>) },
  { key: "transfer", name: "Transferencia bancaria", category: "pagos", logo: Landmark,
    blurb: "El cliente adjunta el comprobante; vos lo cotejás en tu banco y acreditás el pedido.",
    status: () => "on", detail: () => <p>Activa. Un comprobante nunca acredita solo: el pedido pasa a pagado cuando confirmás la transferencia en <a href="#/pedidos">Pedidos</a>.</p> },
  { key: "sheets", name: "Google Sheets", category: "catalogo", logo: siGooglesheets,
    blurb: "Tu planilla como catálogo vivo: precios y stock se sincronizan cada 15 minutos.",
    status: (c) => (c.sheet ? "on" : "available"), detail: (c) => <SheetSync onSynced={c.reload} /> },
  { key: "webhooks", name: "Webhooks", category: "automatizacion", logo: Webhook,
    blurb: "Avisos firmados a tu sistema cuando se paga, se cancela, se deriva o se reserva un turno.",
    status: (c) => (c.webhooks ? "on" : "available"), detail: (c) => <WebhooksPanel onChange={c.reload} /> },
  { key: "zapier", name: "Zapier", category: "automatizacion", logo: siZapier,
    blurb: "Conectá con miles de apps (planillas, CRMs, mail) usando nuestros webhooks.",
    status: (c) => (c.webhooks ? "on" : "available"), statusText: (c) => (c.webhooks ? "Vía webhooks" : "Disponible"),
    detail: () => steps(["En Zapier creá un Zap con «Webhooks by Zapier → Catch Hook».", "Copiá la URL que te da.",
      "Pegala en la tarjeta Webhooks de esta página y elegí los eventos.", "Tocá «Probar» y seguí armando el Zap."]) },
  { key: "make", name: "Make", category: "automatizacion", logo: siMake,
    blurb: "Escenarios automáticos con cada venta o derivación, sin programar.",
    status: (c) => (c.webhooks ? "on" : "available"), statusText: (c) => (c.webhooks ? "Vía webhooks" : "Disponible"),
    detail: () => steps(["En Make agregá el módulo «Webhooks → Custom webhook».", "Copiá la dirección.",
      "Pegala en la tarjeta Webhooks y tocá «Probar»."]) },
  { key: "webchat", name: "Chat para tu web", category: "canales", logo: MessageSquareCode,
    blurb: "Un botón «¿Te ayudo?» en tu página con tu agente, carrito y cobro verificado.",
    status: () => "available", detail: () => <WebChatSnippet /> },
  { key: "georef", name: "Georef (datos.gob.ar)", category: "operacion", logo: MapPin,
    blurb: "Entiende «Bernal» o «Ramos Mejía» y lo cruza con tus zonas de envío.",
    status: () => "on", detail: () => <p>Activa y gratuita. Cargá tus zonas en <a href="#/agente">Ajustes del agente → Políticas</a> (ej.: «Quilmes: 4000, Zona Oeste»).</p> },
  { key: "gcal", name: "Google Calendar", category: "operacion", logo: siGooglecalendar,
    blurb: "Tus turnos del chat en tu calendario.", status: () => "soon" },
  { key: "tiendanube", name: "Tiendanube", category: "catalogo", logo: { mono: "TN", color: "#2b3a67" },
    blurb: "Catálogo y stock de tu tienda online, sincronizados.", status: () => "soon" },
  { key: "shopify", name: "Shopify", category: "catalogo", logo: siShopify,
    blurb: "Productos y stock de tu Shopify en el agente.", status: () => "soon" },
  { key: "woocommerce", name: "WooCommerce", category: "catalogo", logo: siWoocommerce,
    blurb: "Tu tienda WordPress como catálogo del agente.", status: () => "soon" },
  { key: "mercadolibre", name: "Mercado Libre", category: "canales", logo: { mono: "ML", color: "#ffe600", ink: "#2d3277" },
    blurb: "Responder preguntas de compradores con tu stock real.", status: () => "soon" },
  { key: "whatsapp", name: "WhatsApp", category: "canales", logo: siWhatsapp,
    blurb: "El mismo agente en WhatsApp, con recordatorios de pago y turnos.", status: () => "soon" },
  { key: "instagram", name: "Instagram", category: "canales", logo: siInstagram,
    blurb: "Responder mensajes directos con tu catálogo.", status: () => "soon" },
];

function Logo({ logo }: { logo: Item["logo"] }) {
  if (typeof logo === "function" || (typeof logo === "object" && "$$typeof" in logo)) {
    const Icon = logo as LucideIcon;
    return <span className="intg-logo intg-logo-neutral"><Icon size={22} strokeWidth={1.8} aria-hidden /></span>;
  }
  if ("mono" in logo) {
    return <span className="intg-logo" style={{ background: logo.color, color: logo.ink ?? "#fff" }} aria-hidden>{logo.mono}</span>;
  }
  return (
    <span className="intg-logo" style={{ background: `#${logo.hex}1a` }} aria-hidden>
      <svg viewBox="0 0 24 24" width="22" height="22" fill={`#${logo.hex}`}><path d={logo.path} /></svg>
    </span>
  );
}

const STATUS_LABEL: Record<Status, string> = { on: "Conectada", available: "Disponible", soon: "Próximamente" };

/** Integraciones como catálogo: logo, estado y configuración en el lugar. */
export function Integrations() {
  const [health, setHealth] = useState<Health | null>(null);
  const [sheet, setSheet] = useState(false);
  const [webhooks, setWebhooks] = useState(0);
  const [cat, setCat] = useState<Category | "todas">("todas");
  const [open, setOpen] = useState<string | null>(null);

  const reload = useCallback(() => {
    api.health().then(setHealth, () => setHealth(null));
    api.catalogSheet().then((r) => setSheet(Boolean(r.sheet)), () => setSheet(false));
    api.webhooks().then((w) => setWebhooks(w.endpoints.length), () => setWebhooks(0));
  }, []);
  useEffect(reload, [reload]);

  const ctx: Ctx = { health, sheet, webhooks, reload };
  const list = ITEMS.filter((i) => cat === "todas" || i.category === cat);
  const order: Record<Status, number> = { on: 0, available: 1, soon: 2 };
  list.sort((a, b) => order[a.status(ctx)] - order[b.status(ctx)]);
  const active = ITEMS.find((i) => i.key === open);
  const connected = ITEMS.filter((i) => i.status(ctx) === "on").length;

  return (
    <div className="sheet">
      <PageHeader title="Integraciones"
        description={`${connected} conectadas. Conectá tu catálogo, tus cobros y tus otros sistemas; lo marcado «Próximamente» está en camino.`} />
      <div className="results-range intg-filters" role="group" aria-label="Categoría">
        {CATEGORIES.map((c) => (
          <button key={c.key} type="button" className="chip" aria-pressed={cat === c.key} onClick={() => setCat(c.key)}>{c.label}</button>
        ))}
      </div>
      <ul className="intg-grid">
        {list.map((i) => {
          const st = i.status(ctx);
          return (
            <li key={i.key}>
              <button type="button" className={`intg-card intg-${st}${open === i.key ? " is-open" : ""}`}
                aria-expanded={open === i.key} disabled={st === "soon"}
                onClick={() => setOpen(open === i.key ? null : i.key)}>
                <span className="intg-head">
                  <Logo logo={i.logo} />
                  <span className={`intg-status intg-status-${st}`}>
                    <span className="dot" aria-hidden />{i.statusText?.(ctx) ?? STATUS_LABEL[st]}
                  </span>
                </span>
                <b>{i.name}</b>
                <span className="muted small">{i.blurb}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {active?.detail && (
        <section className="intg-detail results-card" aria-labelledby="intg-detail-title">
          <div className="intg-detail-head">
            <Logo logo={active.logo} />
            <h2 id="intg-detail-title">{active.name}</h2>
            <button className="btn sm ghost" type="button" aria-label="Cerrar" onClick={() => setOpen(null)}>
              <X size={16} strokeWidth={1.8} aria-hidden />
            </button>
          </div>
          {active.detail(ctx)}
        </section>
      )}
    </div>
  );
}
