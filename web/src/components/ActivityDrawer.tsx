import { useEffect, useState } from "react";
import { api, type Activity, type Company, type Opportunity } from "../lib/api";
import { STAGE_LABEL, fmtAmount, pedidoText } from "../lib/format";

const KIND_LABEL: Record<string, string> = {
  creada: "Creada",
  cambio_estado: "Cambio de estado",
  seguimiento: "Seguimiento",
  nota: "Nota",
};

function fmtWhen(iso: string): string {
  try {
    return new Date(iso.replace(" ", "T")).toLocaleString("es-AR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function ActivityDrawer({
  opp,
  company,
  onClose,
}: {
  opp: Opportunity | null;
  company: Company;
  onClose: () => void;
}) {
  const [items, setItems] = useState<Activity[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!opp) return;
    setItems(null);
    setError(false);
    api
      .activity(company, opp.id)
      .then(setItems)
      .catch(() => setError(true));
  }, [opp, company]);

  useEffect(() => {
    if (!opp) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [opp, onClose]);

  if (!opp) return null;
  const p = pedidoText(opp.requirements);

  return (
    <>
      <div className="drawer-scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Actividad de la oportunidad">
        <div className="drawer-head">
          <div>
            <h2>{p.main || "Consulta"}</h2>
            {p.sub && <p className="drawer-sub">{p.sub}</p>}
          </div>
          <button className="btn ghost sm" type="button" onClick={onClose} aria-label="Cerrar">
            Cerrar
          </button>
        </div>

        <div className="drawer-meta">
          <div>
            <span className="l">Estado</span>
            <span className="v">{STAGE_LABEL[opp.stage] || opp.stage}</span>
          </div>
          <div>
            <span className="l">Importe</span>
            <span className="v mono">{opp.estimated_amount != null ? `$ ${fmtAmount(opp.estimated_amount)}` : "—"}</span>
          </div>
          <div>
            <span className="l">Seguimiento</span>
            <span className="v mono">{opp.next_action_at ? String(opp.next_action_at).slice(0, 10) : "—"}</span>
          </div>
        </div>

        <h3 className="drawer-h3">Actividad</h3>
        {error ? (
          <div className="empty-box">No pude cargar la actividad.</div>
        ) : items === null ? (
          <div className="timeline">
            {Array.from({ length: 3 }).map((_, i) => (
              <div className="tl-item" key={i}>
                <span className="tl-dot" />
                <span className="skel" style={{ width: 160, height: 12 }} />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-box">Sin actividad registrada todavía.</div>
        ) : (
          <ol className="timeline">
            {items.map((a, i) => (
              <li className="tl-item" key={i}>
                <span className="tl-dot" />
                <div className="tl-body">
                  <div className="tl-top">
                    <span className="tl-kind">{KIND_LABEL[a.kind] || a.kind}</span>
                    <span className="tl-when mono">{fmtWhen(a.created_at)}</span>
                  </div>
                  {a.detail && <div className="tl-detail">{a.detail}</div>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </aside>
    </>
  );
}
