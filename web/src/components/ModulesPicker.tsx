import { useEffect, useState } from "react";
import { ApiError, api, type ModuleInfo, type Modules } from "../lib/api";
import { useSession } from "../lib/session";

/** Lo más común para un negocio que recién empieza: el resto lo prende quien lo necesita. */
export const STARTER_MODULES: Modules = {
  turnos: false, reparto: false, correo: true, retiro: true, senas: false, campanias: true,
};

/** Qué usa el negocio. Ordena el panel y el asistente; apagar un módulo no borra datos.
 *  `initial` permite proponer una selección (negocio nuevo) que recién se guarda al tocar «Guardar». */
export function ModulesPicker({ initial, savedNote }: {
  initial?: (saved: Modules) => Modules;
  savedNote?: string;
}) {
  const { setModules } = useSession();
  const [catalog, setCatalog] = useState<ModuleInfo[] | null>(null);
  const [saved, setSaved] = useState<Modules | null>(null);
  const [sel, setSel] = useState<Modules | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    let alive = true;
    api.modules()
      .then((r) => {
        if (!alive) return;
        setCatalog(r.catalog);
        setSaved(r.modules);
        setSel(initial ? initial(r.modules) : r.modules);
      })
      .catch(() => alive && setMsg({ ok: false, text: "No pude cargar los módulos." }));
    return () => {
      alive = false;
    };
    // `initial` se evalúa una sola vez, con lo guardado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!catalog || !sel || !saved) {
    return <div className={`state${msg ? " err" : ""}`} role={msg ? "alert" : undefined}>{msg?.text ?? "Cargando…"}</div>;
  }
  const dirty = catalog.some((m) => sel[m.key] !== saved[m.key]);

  async function save() {
    if (!sel) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.saveModules(sel);
      setSaved(r.modules);
      setSel(r.modules);
      setModules(r.modules);
      setMsg({ ok: true, text: savedNote ?? "Guardado. El menú ya muestra sólo lo que usás." });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : "No pude guardar los módulos." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <fieldset className="module-choice">
        <legend className="sr">Módulos que usa tu negocio</legend>
        {catalog.map((m) => (
          <label key={m.key} className={sel[m.key] ? "on" : ""}>
            <input type="checkbox" checked={sel[m.key]}
              onChange={(e) => { setMsg(null); setSel({ ...sel, [m.key]: e.target.checked }); }} />
            <span><b>{m.label}</b><small className="muted">{m.hint}</small></span>
          </label>
        ))}
      </fieldset>
      <div className="inline">
        <button className="btn primary sm" type="button" disabled={busy || !dirty} onClick={() => void save()}>
          {busy ? "Guardando…" : "Guardar módulos"}
        </button>
        {msg && <span className={`pill ${msg.ok ? "pos" : "neg"}`} role="status">{msg.text}</span>}
        {!msg && dirty && <span className="muted">Sin guardar</span>}
      </div>
    </>
  );
}
