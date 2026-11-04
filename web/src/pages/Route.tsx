import { useCallback, useEffect, useState } from "react";
import { Check, MapPin, MessageCircle, Phone, Truck } from "lucide-react";
import { Badge, EmptyState } from "../components/ui";
import { api, type RouteDay, type RouteJob, type RouteStep } from "../lib/api";
import { dayLabel, itemsText, localDay, shiftDay } from "../lib/format";
import { DELIVERY_TONE } from "./Deliveries";

const REFRESH_MS = 30_000;
const ACTIVE = new Set(["scheduled", "on_the_way", "arrived"]);
const ETA_CHIPS = [10, 20, 30, 45, 60];
const FAIL_CHIPS = ["No había nadie", "Dirección incorrecta", "El cliente reprogramó"];
const MSG_CHIPS = ["Estoy en la puerta", "Llego en 10 minutos", "¿Hay alguien para recibir?"];

const errText = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);
const hour = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }) : "";

/** Hoja de ruta del repartidor: sólo sus entregas, pensada para el celular en la calle.
 *  Cada paso le avisa al cliente por su chat y hace avanzar el pedido. */
export function RoutePage() {
  const [day, setDay] = useState(localDay);
  const [data, setData] = useState<RouteDay | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.route(day).then((d) => { setData(d); setError(null); },
      (e) => setError(errText(e, "No pude cargar tu hoja de ruta.")));
  }, [day]);

  // Se relee cada 30 s y al volver a la app (el celular suele quedar en el bolsillo).
  useEffect(() => {
    load();
    const t = window.setInterval(load, REFRESH_MS);
    window.addEventListener("focus", load);
    const onVisible = () => document.visibilityState === "visible" && load();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(t);
      window.removeEventListener("focus", load);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  const shown = data && data.date === day ? data : null;
  const active = shown?.jobs.filter((j) => ACTIVE.has(j.status)) ?? [];
  const closed = shown?.jobs.filter((j) => !ACTIVE.has(j.status)) ?? [];
  const today = localDay();
  const tomorrow = shiftDay(today, 1);

  return (
    <div className="sheet rt">
      <header className="rt-head">
        <h1>Mi hoja de ruta</h1>
        <div className="rt-days" role="group" aria-label="Día">
          <button className="chip" type="button" aria-pressed={day === today} onClick={() => setDay(today)}>Hoy</button>
          <button className="chip" type="button" aria-pressed={day === tomorrow} onClick={() => setDay(tomorrow)}>Mañana</button>
        </div>
      </header>
      {error && (
        <p className="state err" role="alert">
          {error}{" "}
          <button className="btn sm" type="button" onClick={load}>Reintentar</button>
        </p>
      )}
      {!shown ? (!error && <div className="state">Cargando…</div>) : (
        <>
          {active.length === 0 ? (
            <EmptyState icon={Truck} title={closed.length ? "Terminaste todo por hoy" : `No tenés entregas ${day === today ? "hoy" : day === tomorrow ? "mañana" : dayLabel(day)}`}>
              {closed.length ? "Abajo quedó el resumen." : "Cuando te asignen una, aparece acá."}
            </EmptyState>
          ) : (
            <ol className="rt-list" aria-label="Entregas pendientes">
              {active.map((j) => <RouteCard key={j.id} job={j} onChanged={load} />)}
            </ol>
          )}
          {closed.length > 0 && (
            <section className="rt-closed" aria-labelledby="rt-closed-title">
              <h2 id="rt-closed-title">Terminadas <span className="muted">{closed.length}</span></h2>
              <ul>
                {closed.map((j) => (
                  <li key={j.id}>
                    <span><b>#{j.order_number}</b> {j.contact.name}</span>
                    <Badge tone={DELIVERY_TONE[j.status] ?? "neu"}>{j.status_label}</Badge>
                    {j.finished_at && <span className="muted small">{hour(j.finished_at)}</span>}
                    {j.failure_reason && <span className="muted small rt-reason">{j.failure_reason}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}

type Panel = null | "eta" | "fail";

function RouteCard({ job, onChanged }: { job: RouteJob; onChanged: () => void }) {
  const [panel, setPanel] = useState<Panel>(null);
  const [reason, setReason] = useState("");
  const [other, setOther] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const install = job.kind.includes("install");
  const doneLabel = install ? "Entregado e instalado" : "Entregado";

  async function step(body: RouteStep) {
    setBusy(true);
    setError(null);
    try {
      await api.routeStatus(job.id, body);
      setPanel(null);
      onChanged();
    } catch (e) {
      setError(errText(e, "No se pudo guardar el paso."));
    } finally {
      setBusy(false);
    }
  }

  async function message(t: string) {
    const body = t.trim();
    if (!body) return;
    setBusy(true);
    setError(null);
    setSent(null);
    try {
      await api.routeMessage(job.id, body);
      setText("");
      setSent(body);
    } catch (e) {
      setError(errText(e, "No se pudo mandar el mensaje."));
    } finally {
      setBusy(false);
    }
  }

  const failReason = other ? reason.trim() : reason;
  return (
    <li className="rt-card">
      <div className="rt-top">
        <span className="rt-when">{job.window_label} · {job.kind_label}</span>
        <Badge tone={DELIVERY_TONE[job.status] ?? "neu"}>{job.status_label}</Badge>
      </div>
      <h2 className="rt-title">Pedido #{job.order_number}</h2>
      <p className="rt-items">{itemsText(job.items)}</p>

      <div className="rt-row">
        <span className="rt-addr"><MapPin size={16} strokeWidth={1.8} aria-hidden /> {job.address || "Sin dirección"}</span>
        {job.maps_url && (
          <a className="btn rt-btn" href={job.maps_url} target="_blank" rel="noopener noreferrer">Abrir en Maps</a>
        )}
      </div>
      <div className="rt-row">
        <span>{job.contact.name || "Sin nombre"}{job.contact.phone && <span className="muted"> · {job.contact.phone}</span>}</span>
        {job.contact.phone && (
          <a className="btn rt-btn" href={`tel:${job.contact.phone}`}>
            <Phone size={16} strokeWidth={1.8} aria-hidden /> Llamar
          </a>
        )}
      </div>
      {job.note && <p className="rt-note"><b>Nota del negocio:</b> {job.note}</p>}
      {job.delivery_note && <p className="rt-note"><b>Indicaciones del cliente:</b> {job.delivery_note}</p>}
      {job.status === "on_the_way" && job.eta_minutes != null && (
        <p className="muted small">Le dijiste que llegabas en ~{job.eta_minutes} min{job.started_at ? ` (salida ${hour(job.started_at)})` : ""}.</p>
      )}
      {job.customer_messages.length > 0 && (
        <div className="rt-msgs" aria-label="Lo último que escribió el cliente">
          <span className="muted small">El cliente escribió:</span>
          {job.customer_messages.map((m, i) => (
            <blockquote key={`${m.at}-${i}`} className="rt-quote">
              {m.text}<span className="muted small"> · {hour(m.at)}</span>
            </blockquote>
          ))}
        </div>
      )}

      {panel === null && (
        <div className="rt-steps">
          {job.status === "scheduled" && (
            <button className="btn primary rt-btn rt-main" type="button" disabled={busy} onClick={() => setPanel("eta")}>
              <Truck size={18} strokeWidth={1.8} aria-hidden /> Salí
            </button>
          )}
          {job.status === "on_the_way" && (
            <button className="btn primary rt-btn rt-main" type="button" disabled={busy} onClick={() => void step({ status: "arrived" })}>
              <MapPin size={18} strokeWidth={1.8} aria-hidden /> Llegué
            </button>
          )}
          {(job.status === "on_the_way" || job.status === "arrived") && (
            <button className={`btn rt-btn rt-main${job.status === "arrived" ? " primary" : ""}`} type="button" disabled={busy}
              onClick={() => window.confirm(`¿Marcar el pedido #${job.order_number} como ${doneLabel.toLowerCase()}?`) && void step({ status: "done" })}>
              <Check size={18} strokeWidth={2} aria-hidden /> {doneLabel}
            </button>
          )}
          <button className="btn ghost rt-btn" type="button" disabled={busy} onClick={() => { setReason(""); setOther(false); setPanel("fail"); }}>
            No pude entregar
          </button>
        </div>
      )}

      {panel === "eta" && (
        <div className="rt-panel" role="group" aria-labelledby={`eta-${job.id}`}>
          <b id={`eta-${job.id}`}>¿En cuántos minutos llegás?</b>
          <div className="rt-chips">
            {ETA_CHIPS.map((n) => (
              <button key={n} className="chip rt-chip" type="button" disabled={busy}
                onClick={() => void step({ status: "on_the_way", eta_minutes: n })}>{n} min</button>
            ))}
          </div>
          <div className="rt-chips">
            <button className="btn rt-btn" type="button" disabled={busy} onClick={() => void step({ status: "on_the_way" })}>Salir sin decir</button>
            <button className="btn ghost rt-btn" type="button" disabled={busy} onClick={() => setPanel(null)}>Volver</button>
          </div>
        </div>
      )}

      {panel === "fail" && (
        <form className="rt-panel" aria-labelledby={`fail-${job.id}`}
          onSubmit={(e) => { e.preventDefault(); if (failReason) void step({ status: "failed", reason: failReason }); }}>
          <b id={`fail-${job.id}`}>¿Qué pasó?</b>
          <div className="rt-chips">
            {FAIL_CHIPS.map((r) => (
              <button key={r} className="chip rt-chip" type="button" aria-pressed={!other && reason === r}
                onClick={() => { setOther(false); setReason(r); }}>{r}</button>
            ))}
            <button className="chip rt-chip" type="button" aria-pressed={other}
              onClick={() => { setOther(true); setReason(""); }}>Otro</button>
          </div>
          {other && (
            <label className="field" htmlFor={`why-${job.id}`}><span>Contá qué pasó</span>
              <textarea id={`why-${job.id}`} rows={2} maxLength={300} required value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
          )}
          <p className="muted small">Le avisamos al cliente y el negocio la vuelve a agendar.</p>
          <div className="rt-chips">
            <button className="btn primary rt-btn" type="submit" disabled={busy || !failReason}>Avisar que no se pudo</button>
            <button className="btn ghost rt-btn" type="button" disabled={busy} onClick={() => setPanel(null)}>Volver</button>
          </div>
        </form>
      )}

      <form className="rt-write" onSubmit={(e) => { e.preventDefault(); void message(text); }}>
        <span className="rt-write-label"><MessageCircle size={15} strokeWidth={1.8} aria-hidden /> Escribirle al cliente</span>
        <div className="rt-chips">
          {MSG_CHIPS.map((m) => (
            <button key={m} className="chip rt-chip" type="button" disabled={busy} onClick={() => void message(m)}>{m}</button>
          ))}
        </div>
        <div className="rt-compose">
          <label className="sr" htmlFor={`msg-${job.id}`}>Mensaje para el cliente</label>
          <input id={`msg-${job.id}`} type="text" maxLength={300} placeholder="Escribí un mensaje corto" value={text}
            onChange={(e) => setText(e.target.value)} />
          <button className="btn rt-btn" type="submit" disabled={busy || !text.trim()}>Enviar</button>
        </div>
        {sent && <p className="small rt-sent" role="status"><Check size={14} strokeWidth={2} aria-hidden /> Enviado: «{sent}»</p>}
      </form>
      {error && <p className="state err" role="alert">{error}</p>}
    </li>
  );
}
