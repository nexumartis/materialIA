import { useCallback, useEffect, useState } from "react";
import { CalendarClock, ChevronLeft, ChevronRight, MapPin, Phone, Truck } from "lucide-react";
import { Badge, EmptyState, PageHeader, type BadgeTone } from "../components/ui";
import { api, type Deliveries as Board, type DeliveryJob, type DeliveryStatus, type PendingDelivery } from "../lib/api";
import { dayLabel, fmtAmount, itemsText, localDay, shiftDay } from "../lib/format";

const REFRESH_MS = 30_000;
const money = (n: number) => `$${fmtAmount(Math.round(n))}`;

export const DELIVERY_TONE: Record<DeliveryStatus, BadgeTone> = {
  scheduled: "neu", on_the_way: "info", arrived: "info", done: "pos", failed: "neg", cancelled: "neu",
};

/** Nombre corto de quien reparte: la parte del email antes de la arroba. */
export const personName = (email: string | null) => (email ? email.split("@")[0] : "—");

const errText = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

/** Entregas: el dueño o el equipo agenda los pedidos pagados con envío y sigue el día de reparto. */
export function Deliveries() {
  const [day, setDay] = useState(localDay);
  const [data, setData] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.deliveries(day).then((d) => { setData(d); setError(null); },
      (e) => setError(errText(e, "No pude cargar las entregas.")));
  }, [day]);

  // Al cambiar de día se descarta lo del día anterior; después se relee cada 30 s.
  useEffect(() => {
    setData((d) => (d && d.date === day ? d : null));
    load();
    const t = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(t);
  }, [day, load]);

  const shown = data && data.date === day ? data : null;
  return (
    <div className="sheet">
      <PageHeader title="Entregas"
        description="Agendá las entregas e instalaciones de los pedidos pagados. Quien reparte ve su hoja de ruta en el celular y cada paso le avisa al cliente por el chat." />
      <DayPicker day={day} onChange={setDay} />
      {error && (
        <p className="state err" role="alert">
          {error}{" "}
          <button className="btn sm" type="button" onClick={load}>Reintentar</button>
        </p>
      )}
      {!shown ? (!error && <div className="state">Cargando…</div>) : (
        <div className="dl-grid">
          <PendingList board={shown} day={day} onScheduled={load} />
          <DayJobs board={shown} onChanged={load} />
        </div>
      )}
    </div>
  );
}

function DayPicker({ day, onChange }: { day: string; onChange: (d: string) => void }) {
  const today = localDay();
  return (
    <div className="dl-days" role="group" aria-label="Día">
      <button className="btn icon" type="button" aria-label="Día anterior" onClick={() => onChange(shiftDay(day, -1))}>
        <ChevronLeft size={18} strokeWidth={1.8} aria-hidden />
      </button>
      <button className="chip" type="button" aria-pressed={day === today} onClick={() => onChange(today)}>Hoy</button>
      <button className="chip" type="button" aria-pressed={day === shiftDay(today, 1)} onClick={() => onChange(shiftDay(today, 1))}>Mañana</button>
      <input className="date-input" type="date" aria-label="Elegir día" value={day}
        onChange={(e) => e.target.value && onChange(e.target.value)} />
      <button className="btn icon" type="button" aria-label="Día siguiente" onClick={() => onChange(shiftDay(day, 1))}>
        <ChevronRight size={18} strokeWidth={1.8} aria-hidden />
      </button>
    </div>
  );
}

/** Pedidos pagados con envío a domicilio que todavía no tienen entrega agendada. */
function PendingList({ board, day, onScheduled }: { board: Board; day: string; onScheduled: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section className="panel dl-pending" aria-labelledby="dl-pending-title">
      <header className="panel-head">
        <h2 id="dl-pending-title">Para agendar {board.pending.length > 0 && <span className="muted">{board.pending.length}</span>}</h2>
      </header>
      {board.pending.length === 0 ? (
        <p className="muted small">No hay pedidos pagados con envío esperando fecha. Cuando un cliente pague un pedido con envío a domicilio, aparece acá.</p>
      ) : (
        <ul className="dl-list">
          {board.pending.map((p) => (
            <li key={p.order_id}>
              <PendingRow p={p} />
              {open === p.order_id ? (
                <ScheduleForm board={board} order={p} day={day}
                  onCancel={() => setOpen(null)} onDone={() => { setOpen(null); onScheduled(); }} />
              ) : (
                <button className="btn sm" type="button" onClick={() => setOpen(p.order_id)}>
                  <CalendarClock size={14} strokeWidth={1.8} aria-hidden /> Agendar
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PendingRow({ p }: { p: PendingDelivery }) {
  return (
    <div className="dl-order">
      <div className="dl-line">
        <b>Pedido #{p.order_number}</b>
        <Badge tone="pos">{p.status_label}</Badge>
        <span className="muted small dl-total">{money(p.total)}</span>
      </div>
      <span className="small">{itemsText(p.items)}</span>
      <span className="muted small">{p.address || "Sin dirección"}{p.contact ? ` · ${p.contact}` : ""}</span>
    </div>
  );
}

function driverOptions(board: Board) {
  return board.drivers.map((d) => (
    <option key={d.user_id} value={d.user_id}>
      {d.email ?? "Sin email"}{d.role === "driver" ? "" : d.role === "owner" ? " (dueño)" : " (equipo)"}
    </option>
  ));
}

function ScheduleForm({ board, order, day, onCancel, onDone }: {
  board: Board; order: PendingDelivery; day: string; onCancel: () => void; onDone: () => void;
}) {
  const [date, setDate] = useState(day);
  const [window_, setWindow] = useState(board.windows[0]?.id ?? "");
  const [kind, setKind] = useState(board.kinds[0]?.id ?? "");
  const [driver, setDriver] = useState(board.drivers.find((d) => d.role === "driver")?.user_id ?? "");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const id = `dl-${order.order_id}`;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createDelivery({ order_id: order.order_id, date, window: window_, kind,
        assigned_to: driver || null, note: note.trim() || null });
      onDone();
    } catch (err) {
      setError(errText(err, "No se pudo agendar."));
      setBusy(false);
    }
  }

  return (
    <form className="dl-form" onSubmit={(e) => void submit(e)} aria-label={`Agendar pedido #${order.order_number}`}>
      <div className="dl-form-grid">
        <label className="field" htmlFor={`${id}-date`}><span>Día</span>
          <input id={`${id}-date`} type="date" required min={localDay()} value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className="field" htmlFor={`${id}-win`}><span>Franja</span>
          <select id={`${id}-win`} value={window_} onChange={(e) => setWindow(e.target.value)}>
            {board.windows.map((w) => <option key={w.id} value={w.id}>{w.label}</option>)}
          </select>
        </label>
        <label className="field" htmlFor={`${id}-kind`}><span>Tipo</span>
          <select id={`${id}-kind`} value={kind} onChange={(e) => setKind(e.target.value)}>
            {board.kinds.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
          </select>
        </label>
        <label className="field" htmlFor={`${id}-drv`}><span>Quién va</span>
          <select id={`${id}-drv`} value={driver} onChange={(e) => setDriver(e.target.value)}>
            <option value="">Sin asignar</option>
            {driverOptions(board)}
          </select>
        </label>
      </div>
      <label className="field" htmlFor={`${id}-note`}><span>Nota interna para el repartidor</span>
        <textarea id={`${id}-note`} rows={2} maxLength={500} placeholder="Ej.: llevar la base aparte, subir por escalera."
          value={note} onChange={(e) => setNote(e.target.value)} />
        <small>El cliente no la ve. Al agendar, le avisamos por el chat el día y la franja.</small>
      </label>
      {error && <p className="state err" role="alert">{error}</p>}
      <div className="inline">
        <button className="btn primary sm" type="submit" disabled={busy || !date || !window_ || !kind}>
          {busy ? "Agendando…" : "Agendar"}
        </button>
        <button className="btn sm ghost" type="button" onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  );
}

/** Entregas del día agrupadas por franja horaria. */
function DayJobs({ board, onChanged }: { board: Board; onChanged: () => void }) {
  const groups = board.windows
    .map((w) => ({ ...w, jobs: board.jobs.filter((j) => j.window === w.id) }))
    .filter((g) => g.jobs.length > 0);
  return (
    <section className="panel dl-day" aria-labelledby="dl-day-title">
      <header className="panel-head">
        <h2 id="dl-day-title">{dayLabel(board.date)} {board.jobs.length > 0 && <span className="muted">{board.jobs.length}</span>}</h2>
      </header>
      {groups.length === 0 ? (
        <EmptyState icon={Truck} title="No hay entregas para este día">
          Agendá un pedido de «Para agendar» o elegí otro día.
        </EmptyState>
      ) : groups.map((g) => (
        <div className="dl-window" key={g.id}>
          <h3>{g.label}</h3>
          <ul className="dl-list">
            {g.jobs.map((j) => <JobRow key={j.id} job={j} board={board} onChanged={onChanged} />)}
          </ul>
        </div>
      ))}
    </section>
  );
}

function JobRow({ job, board, onChanged }: { job: DeliveryJob; board: Board; onChanged: () => void }) {
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
    <li className="dl-job">
      <div className="dl-line">
        <b>Pedido #{job.order_number}</b>
        <span className="muted small">{job.kind_label}</span>
        <Badge tone={DELIVERY_TONE[job.status] ?? "neu"}>{job.status_label}</Badge>
        {job.status === "on_the_way" && job.eta_minutes != null && (
          <span className="small dl-eta">Llega en ~{job.eta_minutes} min</span>
        )}
      </div>
      <span className="small">{itemsText(job.items)}</span>
      <span className="small dl-meta">
        <MapPin size={14} strokeWidth={1.8} aria-hidden />
        {job.maps_url ? <a className="link" href={job.maps_url} target="_blank" rel="noopener noreferrer">{job.address}</a> : job.address || "Sin dirección"}
      </span>
      <span className="small dl-meta">
        <Phone size={14} strokeWidth={1.8} aria-hidden />
        {job.contact.name || "Sin nombre"}
        {job.contact.phone && <> · <a className="link" href={`tel:${job.contact.phone}`}>{job.contact.phone}</a></>}
      </span>
      <span className="small muted">Va: {job.assigned_to ? personName(job.driver_email) : "sin asignar"}</span>
      {job.note && <span className="small muted">Nota: {job.note}</span>}
      {job.failure_reason && <span className="small dl-fail">No se pudo: {job.failure_reason}</span>}

      {editable && (
        <div className="dl-actions">
          <label className="sr" htmlFor={`re-${job.id}`}>Reasignar pedido #{job.order_number}</label>
          <select id={`re-${job.id}`} className="field-select dl-select" disabled={busy} value={job.assigned_to ?? ""}
            onChange={(e) => void patch({ assigned_to: e.target.value || null })}>
            <option value="">Sin asignar</option>
            {driverOptions(board)}
          </select>
          <button className="btn sm" type="button" aria-expanded={moving} onClick={() => setMoving((v) => !v)}>Cambiar día o franja</button>
          <button className="btn sm ghost" type="button" disabled={busy}
            onClick={() => window.confirm(`¿Cancelar la entrega del pedido #${job.order_number}? Vuelve a «Para agendar».`)
              && void patch({ status: "cancelled" })}>
            Cancelar
          </button>
        </div>
      )}
      {editable && moving && (
        <form className="dl-move" onSubmit={(e) => { e.preventDefault(); void patch({ date, window: window_ }); }}>
          <label className="field" htmlFor={`mv-d-${job.id}`}><span>Día</span>
            <input id={`mv-d-${job.id}`} type="date" required min={localDay()} value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label className="field" htmlFor={`mv-w-${job.id}`}><span>Franja</span>
            <select id={`mv-w-${job.id}`} value={window_} onChange={(e) => setWindow(e.target.value)}>
              {board.windows.map((w) => <option key={w.id} value={w.id}>{w.label}</option>)}
            </select>
          </label>
          <button className="btn sm primary" type="submit" disabled={busy || (date === job.date && window_ === job.window)}>Guardar</button>
        </form>
      )}
      {error && <p className="state err" role="alert">{error}</p>}
    </li>
  );
}
