import { useCallback, useEffect, useState } from "react";
import { api, type Company, type Opportunity, type Stage } from "../lib/api";
import { STAGES, dateOnly, fmtDate, isOverdue, pedidoText } from "../lib/format";

export function Opportunities({ company }: { company: Company }) {
  const [list, setList] = useState<Opportunity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyOver, setOnlyOver] = useState(false);
  const [stamp, setStamp] = useState("");

  const load = useCallback(() => {
    setList(null);
    setError(null);
    api
      .opportunities(company)
      .then((d) => {
        setList(d);
        setStamp(
          new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
        );
      })
      .catch(() => {
        setList([]);
        setError("No pude conectar con la API.");
      });
  }, [company]);

  useEffect(load, [load]);

  const data = list ?? [];
  const overdue = data.filter(isOverdue).length;
  const count = (s: Stage) => data.filter((o) => o.stage === s).length;
  const kpis: { label: string; n: number; neg?: boolean }[] = [
    { label: "Total", n: data.length },
    { label: "Vencidas", n: overdue, neg: overdue > 0 },
    { label: "Para cotizar", n: count("para_cotizar") },
    { label: "Cerradas", n: count("cerrada") },
  ];
  const view = onlyOver ? data.filter(isOverdue) : data;

  const onSaved = (updated: Opportunity) =>
    setList((cur) => (cur ? cur.map((o) => (o.id === updated.id ? updated : o)) : cur));

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Oportunidades</h1>
          <p className="finding">
            {error ? (
              "Sin conexión con la API."
            ) : overdue ? (
              <>
                <b>{overdue}</b>{" "}
                {overdue === 1 ? "oportunidad necesita" : "oportunidades necesitan"} seguimiento
                hoy. Su fecha ya venció.
              </>
            ) : list === null ? (
              "Cargando…"
            ) : (
              "Ningún seguimiento vencido. Todo al día."
            )}
          </p>
        </div>
        <div className="right">
          {stamp && !error && <span className="stamp">Actualizado {stamp}</span>}
          <button className="btn ghost sm" type="button" onClick={load}>
            Actualizar
          </button>
        </div>
      </div>

      {!error && (
        <section className="kpis" aria-label="Resumen">
          {kpis.map((k) => (
            <div className="kpi" key={k.label}>
              <div className="l">{k.label}</div>
              <div className={`n num${k.neg ? " neg" : ""}`}>{list === null ? "—" : k.n}</div>
            </div>
          ))}
        </section>
      )}

      {!error && (
        <div className="tabs" role="tablist" aria-label="Filtrar">
          <button role="tab" aria-selected={!onlyOver} type="button" onClick={() => setOnlyOver(false)}>
            Todas
          </button>
          <button role="tab" aria-selected={onlyOver} type="button" onClick={() => setOnlyOver(true)}>
            Vencidos{overdue ? ` ${overdue}` : ""}
          </button>
        </div>
      )}

      {!error && (
        <div className="toolbar">
          <span className="count">
            Empresa {company} · {company === "A" ? "Cristalería" : "Aberturas"}
          </span>
          <span className="right count">
            {list === null ? "" : `${view.length} ${view.length === 1 ? "oportunidad" : "oportunidades"}`}
          </span>
        </div>
      )}

      <div className="tablewrap">
        <table>
          <caption className="sr">Oportunidades por empresa</caption>
          <thead>
            <tr>
              <th scope="col">Fecha</th>
              <th scope="col">Pedido</th>
              <th scope="col">Estado</th>
              <th scope="col" className="num">Importe (ARS)</th>
              <th scope="col">Seguimiento</th>
              <th scope="col" className="num">Guardar</th>
            </tr>
          </thead>
          <tbody>
            {error ? (
              <tr>
                <td colSpan={6}>
                  <div className="state err" role="alert">
                    <span className="pill neg">Sin conexión</span>
                    <br />
                    No pude conectar con la API. ¿Está corriendo el backend en el puerto 8077?
                    <br />
                    <button className="btn sm" type="button" style={{ marginTop: 12 }} onClick={load}>
                      Reintentar
                    </button>
                  </div>
                </td>
              </tr>
            ) : list === null ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={6} style={{ padding: 0 }}>
                    <div className="skel-row">
                      <span className="skel" style={{ width: 36 }} />
                      <span className="skel" style={{ width: 180 }} />
                      <span className="skel" style={{ width: 120, marginLeft: "auto" }} />
                    </div>
                  </td>
                </tr>
              ))
            ) : view.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="state" role="status">
                    {onlyOver
                      ? "No hay oportunidades con seguimiento vencido."
                      : "Todavía no hay oportunidades para esta empresa. Generá una desde el Chat demo."}
                  </div>
                </td>
              </tr>
            ) : (
              view.map((o) => <Row key={o.id} o={o} company={company} onSaved={onSaved} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Row({
  o,
  company,
  onSaved,
}: {
  o: Opportunity;
  company: Company;
  onSaved: (u: Opportunity) => void;
}) {
  const [stage, setStage] = useState<Stage>(o.stage);
  const [amount, setAmount] = useState(o.estimated_amount != null ? String(o.estimated_amount) : "");
  const [date, setDate] = useState(dateOnly(o.next_action_at));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; kind: "ok" | "err" } | null>(null);
  const [flash, setFlash] = useState(false);

  const p = pedidoText(o.requirements);
  const over = isOverdue(o);

  async function save() {
    setSaving(true);
    setMsg(null);
    const body: { stage: Stage; estimated_amount?: number; next_action_at?: string } = { stage };
    if (amount !== "") body.estimated_amount = Number(amount);
    if (date !== "") body.next_action_at = date;
    try {
      await api.patchOpportunity(company, o.id, body);
      setMsg({ text: "Guardado", kind: "ok" });
      setFlash(true);
      setTimeout(() => setFlash(false), 1100);
      onSaved({
        ...o,
        stage,
        estimated_amount: amount === "" ? o.estimated_amount : Number(amount),
        next_action_at: date === "" ? o.next_action_at : date,
      });
    } catch {
      setMsg({ text: "Error", kind: "err" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className={`${over ? "overdue" : ""} ${flash ? "saved" : ""}`}>
      <td className="num">{fmtDate(o.created_at)}</td>
      <td className="pedido">
        <b>{p.main || "Consulta"}</b>
        {p.sub && <small>{p.sub}</small>}
      </td>
      <td>
        <select
          className="stage-select"
          aria-label="Estado de la oportunidad"
          value={stage}
          onChange={(e) => setStage(e.target.value as Stage)}
        >
          {STAGES.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
      </td>
      <td className="num">
        <input
          className="amount-input num"
          type="number"
          min={0}
          step={1000}
          placeholder="—"
          aria-label="Importe estimado en pesos"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </td>
      <td>
        <input
          className="date-input"
          type="date"
          aria-label="Fecha de seguimiento"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        {over && <span className="pill neg">Vencido</span>}
      </td>
      <td className="actions-cell">
        <button className="btn sm" type="button" onClick={save} disabled={saving}>
          {saving ? "Guardando…" : "Guardar"}
        </button>
        {msg && (
          <span
            className="rowmsg"
            aria-live="polite"
            style={{ color: msg.kind === "ok" ? "var(--positive)" : "var(--negative)" }}
          >
            {msg.text}
          </span>
        )}
      </td>
    </tr>
  );
}
