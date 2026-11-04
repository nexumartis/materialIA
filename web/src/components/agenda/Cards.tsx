import { useEffect, useRef, useState } from "react";
import { MapPin, MessageCircle, MoreHorizontal, Phone } from "lucide-react";
import { Badge } from "../ui";
import { api, type Appointment, type Deliveries, type DeliveryJob, type DeliveryWindow } from "../../lib/api";
import { itemsText, localDay } from "../../lib/format";
import { Address } from "./PendingQueue";
import { DELIVERY_TONE, DriverOptions, WINDOW_NAME, errText, hhmm, personName } from "./shared";

/** Menú «⋯» chico: se cierra con Escape o al tocar afuera. */
function Overflow({ label, children }: { label: string; children: (close: () => void) => React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);
  return (
    <div className="ag-more" ref={ref}>
      <button className="btn icon ag-more-btn" type="button" aria-label={label} aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <MoreHorizontal size={18} strokeWidth={1.8} aria-hidden />
      </button>
      {open && <div className="ag-menu">{children(() => setOpen(false))}</div>}
    </div>
  );
}

export function AppointmentCard({ appt, onChanged, onError }: {
  appt: Appointment; onChanged: () => void; onError: (msg: string) => void;
}) {
  async function cancel() {
    if (!window.confirm(`¿Cancelar ${appt.service} del ${appt.label}? Avisale al cliente por el chat.`)) return;
    try {
      await api.cancelAppointment(appt.id);
      onChanged();
    } catch (e) {
      onError(errText(e, "No pude cancelar el turno."));
    }
  }
  return (
    <li className="ag-card">
      <div className="ag-card-top">
        <time className="ag-time" dateTime={appt.starts_at}>{hhmm(appt.starts_at)}</time>
        <span className="ag-kind">Turno</span>
        <Overflow label={`Más acciones para el turno de las ${hhmm(appt.starts_at)}`}>
          {(close) => <button type="button" className="danger" onClick={() => { close(); void cancel(); }}>Cancelar turno</button>}
        </Overflow>
      </div>
      <b className="ag-card-title">{appt.service}</b>
      <span className="muted small">Hasta las {hhmm(appt.ends_at)}</span>
      {appt.conversation_id && (
        <a className="link small" href={`#/conversaciones/${appt.conversation_id}`}>Ver conversación con el cliente</a>
      )}
    </li>
  );
}

export function JobCard({ job, board, onChanged }: { job: DeliveryJob; board: Deliveries; onChanged: () => void }) {
  const [moving, setMoving] = useState(false);
  const [date, setDate] = useState(job.date);
  const [window_, setWindow] = useState(job.window);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editable = job.status === "scheduled";

  async function patch(body: Parameters<typeof api.patchDelivery>[1]) {
    setBusy(true);
    setError(null);
    try {
      await api.patchDelivery(job.id, body);
      setMoving(false);
      onChanged();
    } catch (e) {
      setError(errText(e, "No se pudo guardar."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="ag-card">
      <div className="ag-card-top">
        <b className="ag-card-title">Pedido #{job.order_number}</b>
        <Badge tone={DELIVERY_TONE[job.status] ?? "neu"}>{job.status_label}</Badge>
        {editable && (
          <Overflow label={`Más acciones para el pedido #${job.order_number}`}>
            {(close) => (
              <>
                <button type="button" onClick={() => { close(); setMoving(true); }}>Cambiar día o franja</button>
                <button type="button" className="danger" onClick={() => {
                  close();
                  if (window.confirm(`¿Cancelar la entrega del pedido #${job.order_number}? Vuelve a «Falta agendar».`)) void patch({ status: "cancelled" });
                }}>Cancelar entrega</button>
              </>
            )}
          </Overflow>
        )}
      </div>
      <span className="ag-kind ag-kind-line">{job.kind_label}</span>
      <span className="small">{itemsText(job.items)}</span>
      <span className="small ag-meta">
        <MapPin size={14} strokeWidth={1.8} aria-hidden />
        {job.maps_url
          ? <a className="link" href={job.maps_url} target="_blank" rel="noopener noreferrer"><Address text={job.address} /></a>
          : <Address text={job.address} />}
      </span>
      <span className="small ag-meta">
        <Phone size={14} strokeWidth={1.8} aria-hidden />
        {job.contact.name || "Sin nombre"}
        {job.contact.phone && <> · <a className="link" href={`tel:${job.contact.phone}`}>{job.contact.phone}</a></>}
      </span>
      {job.status === "on_the_way" && job.eta_minutes != null && <span className="small ag-eta">Llega en ~{job.eta_minutes} min</span>}
      {job.failure_reason && <span className="small ag-fail">No se pudo: {job.failure_reason}</span>}
      {job.note && <span className="small muted">Nota: {job.note}</span>}
      <div className="ag-card-foot">
        {editable ? (
          <label className="ag-who">
            <span className="muted small">Va</span>
            <select className="field-select" disabled={busy} value={job.assigned_to ?? ""}
              aria-label={`Quién va al pedido #${job.order_number}`}
              onChange={(e) => void patch({ assigned_to: e.target.value || null })}>
              <option value="">Sin asignar</option>
              <DriverOptions board={board} />
            </select>
          </label>
        ) : (
          <span className="small muted">Va: {job.assigned_to ? personName(job.driver_email) : "sin asignar"}</span>
        )}
        {job.source === "chat" && (
          <span className="ag-tag"><MessageCircle size={12} strokeWidth={1.8} aria-hidden /> Lo eligió el cliente en el chat</span>
        )}
      </div>
      {editable && moving && (
        <form className="ag-move" onSubmit={(e) => { e.preventDefault(); void patch({ date, window: window_ }); }}
          aria-label={`Cambiar día o franja del pedido #${job.order_number}`}>
          <label className="field" htmlFor={`mv-d-${job.id}`}><span>Día</span>
            <input id={`mv-d-${job.id}`} type="date" required min={localDay()} value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label className="field" htmlFor={`mv-w-${job.id}`}><span>Franja</span>
            <select id={`mv-w-${job.id}`} value={window_} onChange={(e) => setWindow(e.target.value)}>
              {board.windows.map((w) => <option key={w.id} value={w.id}>{WINDOW_NAME[w.id as DeliveryWindow]?.name ?? w.label}</option>)}
            </select>
          </label>
          <div className="ag-form-actions">
            <button className="btn sm primary" type="submit" disabled={busy || (date === job.date && window_ === job.window)}>Guardar</button>
            <button className="btn sm ghost" type="button" onClick={() => setMoving(false)}>Cancelar</button>
          </div>
        </form>
      )}
      {error && <p className="state err" role="alert">{error}</p>}
    </li>
  );
}
