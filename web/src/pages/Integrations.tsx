import { useCallback, useEffect, useState } from "react";
import { Copy, PlugZap, Trash2 } from "lucide-react";
import { Badge, EmptyState, PageHeader } from "../components/ui";
import { api, type Webhooks } from "../lib/api";

const EVENT_LABEL: Record<string, string> = {
  "order.paid": "Pedido pagado",
  "order.deposit_paid": "Seña cobrada",
  "order.cancelled": "Pedido cancelado",
  "conversation.needs_human": "Conversación derivada a una persona",
  "order.rated": "Pedido calificado",
};
const when = (iso: string) => new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });

/** Webhooks: el negocio recibe eventos firmados en su sistema (planilla, ERP, CRM, Zapier/Make). */
export function Integrations() {
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sheet">
      <PageHeader title="Integraciones"
        description="Webhooks: tu sistema (planilla, ERP, CRM, Zapier o Make) recibe un aviso firmado cuando pasa algo en tu tienda." />
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
      <WebChatSnippet />
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
function WebChatSnippet() {
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
