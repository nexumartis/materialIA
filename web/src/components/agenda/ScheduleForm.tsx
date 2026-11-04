import { useEffect, useState } from "react";
import { api, type Deliveries, type DeliveryWindow, type PendingDelivery, type SlotOption } from "../../lib/api";
import { localDay, shiftDay } from "../../lib/format";
import { DriverOptions, WINDOW_NAME, defaultDriver, errText } from "./shared";

const km = (n: number) => n.toLocaleString("es-AR", { maximumFractionDigits: 1 });
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** Agendar un pedido: primero las franjas sugeridas (con lugar y, si se puede, cerca de otra entrega). */
export function ScheduleForm({ board, order, onCancel, onDone }: {
  board: Deliveries; order: PendingDelivery; onCancel: () => void; onDone: (date: string) => void;
}) {
  const [options, setOptions] = useState<SlotOption[] | null>(null);
  const [pick, setPick] = useState<SlotOption | null>(null);
  const [manual, setManual] = useState(false);
  const [date, setDate] = useState(shiftDay(localDay(), 1));
  const [window_, setWindow] = useState<string>(board.windows[0]?.id ?? "am");
  const [kind, setKind] = useState(board.kinds[0]?.id ?? "");
  const [driver, setDriver] = useState(() => defaultDriver(board));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const id = `ag-${order.order_id}`;

  useEffect(() => {
    let alive = true;
    api.suggestDelivery(order.order_id).then(
      (r) => { if (!alive) return; setOptions(r.options); setPick(r.options[0] ?? null); if (!r.options.length) setManual(true); },
      () => { if (alive) { setOptions([]); setManual(true); } });
    return () => { alive = false; };
  }, [order.order_id]);

  const slot = manual ? { date, window: window_ } : pick;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!slot) return;
    setBusy(true);
    setError(null);
    try {
      await api.createDelivery({ order_id: order.order_id, date: slot.date, window: slot.window, kind,
        assigned_to: driver || null, note: note.trim() || null });
      onDone(slot.date);
    } catch (err) {
      setError(errText(err, "No se pudo agendar."));
      setBusy(false);
    }
  }

  return (
    <form className="ag-form" onSubmit={(e) => void submit(e)} aria-label={`Agendar pedido #${order.order_number}`}>
      <fieldset className="ag-step">
        <legend>1. Cuándo</legend>
        {options === null ? (
          <p className="muted small" role="status">Buscando días con lugar…</p>
        ) : options.length === 0 ? (
          <p className="muted small">No encontré franjas libres en los próximos días. Elegí la fecha a mano.</p>
        ) : (
          <div className="ag-slots" role="group" aria-label="Días sugeridos">
            {options.map((o) => {
              const on = !manual && pick?.date === o.date && pick.window === o.window;
              return (
                <button key={`${o.date}-${o.window}`} type="button" className="ag-slot" aria-pressed={on}
                  onClick={() => { setPick(o); setManual(false); }}>
                  <b>{cap(o.label)}</b>
                  <span className="small">
                    {o.near_km != null && <span className="ag-near">Ya pasamos cerca ({km(o.near_km)} km) · </span>}
                    {o.free === 1 ? "queda 1 lugar" : `quedan ${o.free} lugares`}
                  </span>
                </button>
              );
            })}
          </div>
        )}
        {options !== null && options.length > 0 && (
          <button className="btn sm ghost ag-other" type="button" aria-expanded={manual} onClick={() => setManual((v) => !v)}>
            {manual ? "Usar un día sugerido" : "Otra fecha"}
          </button>
        )}
        {manual && (
          <div className="ag-grid">
            <label className="field" htmlFor={`${id}-date`}><span>Día</span>
              <input id={`${id}-date`} type="date" required min={localDay()} value={date} onChange={(e) => setDate(e.target.value)} />
            </label>
            <label className="field" htmlFor={`${id}-win`}><span>Franja</span>
              <select id={`${id}-win`} value={window_} onChange={(e) => setWindow(e.target.value)}>
                {board.windows.map((w) => {
                  const n = WINDOW_NAME[w.id as DeliveryWindow];
                  return <option key={w.id} value={w.id}>{n ? `${n.name} · ${n.hours}` : w.label}</option>;
                })}
              </select>
            </label>
          </div>
        )}
      </fieldset>

      <fieldset className="ag-step">
        <legend>2. Qué y quién va</legend>
        <div className="ag-grid">
          <label className="field" htmlFor={`${id}-kind`}><span>Tipo</span>
            <select id={`${id}-kind`} value={kind} onChange={(e) => setKind(e.target.value)}>
              {board.kinds.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
            </select>
          </label>
          <label className="field" htmlFor={`${id}-drv`}><span>Quién va</span>
            <select id={`${id}-drv`} value={driver} onChange={(e) => setDriver(e.target.value)}>
              <option value="">Sin asignar</option>
              <DriverOptions board={board} />
            </select>
          </label>
        </div>
        <label className="field" htmlFor={`${id}-note`}><span>Nota para quien reparte (opcional)</span>
          <input id={`${id}-note`} maxLength={500} placeholder="Ej.: llevar la base aparte" value={note}
            onChange={(e) => setNote(e.target.value)} />
        </label>
      </fieldset>

      {error && <p className="state err" role="alert">{error}</p>}
      <div className="ag-form-actions">
        <button className="btn primary" type="submit" disabled={busy || !slot || !slot.date || !kind}>
          {busy ? "Agendando…" : "Agendar"}
        </button>
        <button className="btn ghost" type="button" onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  );
}
