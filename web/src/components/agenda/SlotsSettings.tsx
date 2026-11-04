import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { api, type DeliveryWindow, type SlotsConfig } from "../../lib/api";
import { WEEKDAYS, WEEKDAY_NAMES, WINDOW_NAME, errText } from "./shared";

const ALL_WINDOWS: DeliveryWindow[] = ["am", "pm", "day"];

/** «Cómo repartís» (dueño): con esto el agente ofrece día y franja al vender y el panel sugiere. */
export function SlotsSettings({ config, onSaved }: { config: SlotsConfig; onSaved: () => void }) {
  const [form, setForm] = useState<SlotsConfig>(config);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const key = JSON.stringify(config);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setForm(config), [key]);

  const set = <K extends keyof SlotsConfig>(k: K, v: SlotsConfig[K]) => { setForm((f) => ({ ...f, [k]: v })); setMsg(null); };
  const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const saved = await api.saveSlots({ ...form, days: [...form.days].sort(), windows: ALL_WINDOWS.filter((w) => form.windows.includes(w)) });
      setForm(saved);
      setMsg({ ok: true, text: "Guardado." });
      onSaved();
    } catch (err) {
      setMsg({ ok: false, text: errText(err, "No se pudo guardar.") });
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="ag-settings">
      <summary>
        <span><b>Cómo repartís</b>
          <small className="muted">{form.enabled ? "El agente ofrece día y franja al vender." : "El agente no ofrece días: agendás vos."}</small>
        </span>
        <ChevronDown className="ag-chev" size={18} strokeWidth={1.8} aria-hidden />
      </summary>
      <form className="ag-settings-body" onSubmit={(e) => void save(e)}>
        <label className="check">
          <input type="checkbox" checked={form.enabled} onChange={(e) => set("enabled", e.target.checked)} />
          El agente ofrece día y franja al vender
        </label>
        <fieldset className="ag-fs">
          <legend>Días de reparto</legend>
          <div className="ag-weekdays">
            {WEEKDAYS.map((d, i) => (
              <button key={d} type="button" className="chip ag-wd" aria-pressed={form.days.includes(i)}
                aria-label={WEEKDAY_NAMES[i]} onClick={() => set("days", toggle(form.days, i))}>{d}</button>
            ))}
          </div>
        </fieldset>
        <fieldset className="ag-fs">
          <legend>Franjas</legend>
          <div className="ag-toggles">
            {ALL_WINDOWS.map((w) => (
              <label key={w} className="check">
                <input type="checkbox" checked={form.windows.includes(w)} onChange={() => set("windows", toggle(form.windows, w))} />
                {WINDOW_NAME[w].name} <span className="muted small">{WINDOW_NAME[w].hours}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="ag-grid ag-grid-3">
          <label className="field"><span>Cupo por franja</span>
            <input type="number" min={1} max={200} required value={form.capacity}
              onChange={(e) => set("capacity", Number(e.target.value))} />
            <small>Entregas que entran en una franja.</small>
          </label>
          <label className="field"><span>Días hacia adelante</span>
            <input type="number" min={1} max={30} required value={form.horizon_days}
              onChange={(e) => set("horizon_days", Number(e.target.value))} />
            <small>Hasta cuándo se ofrecen días.</small>
          </label>
          <label className="field"><span>Anticipación mínima (días)</span>
            <input type="number" min={0} max={7} required value={form.lead_days}
              onChange={(e) => set("lead_days", Number(e.target.value))} />
            <small>0 = se puede entregar hoy.</small>
          </label>
        </div>
        <div className="ag-form-actions">
          <button className="btn primary" type="submit" disabled={busy || !form.days.length || !form.windows.length}>
            {busy ? "Guardando…" : "Guardar"}
          </button>
          {msg && <span className={msg.ok ? "small ag-ok" : "small ag-fail"} role={msg.ok ? "status" : "alert"}>{msg.text}</span>}
          {(!form.days.length || !form.windows.length) && <span className="small muted">Elegí al menos un día y una franja.</span>}
        </div>
      </form>
    </details>
  );
}
