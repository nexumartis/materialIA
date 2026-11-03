import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { EmptyState, PageHeader, Stats, type Stat } from "../components/ui";
import { api, type Insights } from "../lib/api";
import { fmtAmount } from "../lib/format";

const RANGES = [7, 30, 90] as const;
const pct = (x: number | null) => (x == null ? "—" : `${Math.round(x * 100)}%`);
const money = (n: number) => `$${fmtAmount(Math.round(n))}`;
const dayLabel = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString("es-AR", { day: "numeric", month: "short" });

/** Resultados del agente (cualquier rubro): conversaciones → ventas, plata cobrada y cuánto resolvió solo. */
export function Results() {
  const [days, setDays] = useState<(typeof RANGES)[number]>(30);
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.insights(days).then(setData, (e) => setError(e instanceof Error ? e.message : "No pude cargar los resultados."));
  }, [days]);

  return (
    <div className="sheet">
      <PageHeader title="Resultados"
        description="Lo que vendió tu agente con pagos verificados. Las conversaciones de prueba no cuentan."
        actions={
          <div className="results-range" role="group" aria-label="Período">
            {RANGES.map((d) => (
              <button key={d} type="button" className="chip" aria-pressed={d === days}
                onClick={() => setDays(d)}>{d} días</button>
            ))}
          </div>
        } />
      {error && <p className="state err" role="alert">{error}</p>}
      {!data ? (!error && <div className="state">Cargando…</div>) : data.funnel.conversations === 0 ? (
        <EmptyState icon={BarChart3} title="Todavía no hay conversaciones en este período">
          Compartí el link de tu tienda: acá vas a ver cuántas consultas terminan en venta.
        </EmptyState>
      ) : <Body data={data} />}
    </div>
  );
}

function Body({ data }: { data: Insights }) {
  const s = data.sales;
  const items: Stat[] = [
    { label: "Ventas cobradas", value: money(s.revenue), hint: `${s.orders} pedido${s.orders === 1 ? "" : "s"} pagado${s.orders === 1 ? "" : "s"}` },
    { label: "Ticket promedio", value: s.average_ticket == null ? "—" : money(s.average_ticket) },
    { label: "Conversión", value: pct(data.conversion), hint: "conversaciones que terminaron en pago" },
    { label: "Resueltas por el agente", value: pct(data.solo_agent_rate),
      hint: data.waiting_human ? `${data.waiting_human} esperando a una persona` : "sin intervención de tu equipo" },
  ];
  return (
    <>
      <Stats label="Resumen del período" items={items} />
      {(s.off_hours_orders > 0 || data.off_hours_conversations > 0) && (
        <p className="results-callout">
          <b>Fuera de horario</b> (noches y fines de semana): {data.off_hours_conversations} conversaciones
          {s.off_hours_orders > 0 && <> y {s.off_hours_orders} venta{s.off_hours_orders === 1 ? "" : "s"} por {money(s.off_hours_revenue)}</>}
          {" "}que atendió tu agente mientras no estabas.
        </p>
      )}
      {data.deposits.orders > 0 && (
        <p className="muted small">Además, {data.deposits.orders} pedido{data.deposits.orders === 1 ? "" : "s"} señado{data.deposits.orders === 1 ? "" : "s"} por {money(data.deposits.amount)} esperando el saldo.</p>
      )}
      <div className="results-grid">
        <Funnel data={data} />
        <DailyChart data={data} />
      </div>
      {data.top_products.length > 0 && (
        <section className="results-card" aria-labelledby="top-title">
          <h2 id="top-title">Lo más vendido</h2>
          <table className="results-table">
            <thead><tr><th>Producto</th><th className="num">Unidades</th><th className="num">Ventas</th></tr></thead>
            <tbody>
              {data.top_products.map((p) => (
                <tr key={p.name}><td>{p.name}</td><td className="num">{p.qty}</td><td className="num">{money(p.revenue)}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <Satisfaction data={data} />
      {data.ai.calls > 0 && (
        <p className="muted small">
          Uso de IA: {data.ai.calls} llamadas{data.ai.cost != null ? ` · costo estimado ${data.ai.cost} ${data.ai.currency}` : ""}.
        </p>
      )}
    </>
  );
}

function Funnel({ data }: { data: Insights }) {
  const f = data.funnel;
  const steps = [
    { label: "Conversaciones", n: f.conversations },
    { label: "Armaron carrito", n: f.with_cart },
    { label: "Confirmaron pedido", n: f.with_order },
    { label: "Pagaron", n: f.with_payment },
  ];
  return (
    <section className="results-card" aria-labelledby="funnel-title">
      <h2 id="funnel-title">De la consulta a la venta</h2>
      <ol className="funnel">
        {steps.map((st) => (
          <li key={st.label}>
            <span className="funnel-label">{st.label}</span>
            <span className="funnel-track" aria-hidden>
              <span className="funnel-bar" style={{ width: `${f.conversations ? Math.max(2, (st.n / f.conversations) * 100) : 0}%` }} />
            </span>
            <span className="funnel-n">{st.n} <small className="muted">{pct(f.conversations ? st.n / f.conversations : null)}</small></span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Ventas cobradas por día: una sola serie (sin doble eje); las conversaciones van en el tooltip y la tabla. */
function DailyChart({ data }: { data: Insights }) {
  const [hover, setHover] = useState<number | null>(null);
  const series = data.series;
  const max = Math.max(...series.map((d) => d.revenue), 1);
  const W = 600, H = 160, gap = 2, bw = W / series.length;
  const active = hover == null ? null : series[hover];
  return (
    <section className="results-card" aria-labelledby="daily-title">
      <h2 id="daily-title">Ventas cobradas por día</h2>
      <div className="daily-readout" aria-live="polite">
        {active ? <><b>{dayLabel(active.day)}</b> · {money(active.revenue)} · {active.conversations} conversaciones</>
          : <span className="muted">Pasá el mouse o el foco por una barra para ver el día.</span>}
      </div>
      <svg className="daily-chart" viewBox={`0 0 ${W} ${H + 1}`} role="img"
        aria-label={`Ventas cobradas por día, máximo ${money(max)}`} onMouseLeave={() => setHover(null)}>
        <line x1={0} x2={W} y1={H} y2={H} className="axis" />
        {series.map((d, i) => {
          const h = d.revenue ? Math.max(3, (d.revenue / max) * (H - 8)) : 0;
          const x = i * bw + gap / 2, w = Math.max(1, bw - gap);
          return (
            <g key={d.day} tabIndex={0} onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              aria-label={`${dayLabel(d.day)}: ${money(d.revenue)}, ${d.conversations} conversaciones`}>
              <rect x={i * bw} y={0} width={bw} height={H} className="hit" />
              {h > 0 && <path className={`bar${hover === i ? " on" : ""}`}
                d={`M${x},${H} v${-(h - Math.min(4, w / 2))} q0,-${Math.min(4, w / 2)} ${Math.min(4, w / 2)},-${Math.min(4, w / 2)} h${w - 2 * Math.min(4, w / 2)} q${Math.min(4, w / 2)},0 ${Math.min(4, w / 2)},${Math.min(4, w / 2)} v${h - Math.min(4, w / 2)} z`} />}
            </g>
          );
        })}
      </svg>
      <div className="daily-ticks" aria-hidden><span>{dayLabel(series[0].day)}</span><span>{dayLabel(series[series.length - 1].day)}</span></div>
      <details className="results-table-toggle">
        <summary>Ver como tabla</summary>
        <table className="results-table">
          <thead><tr><th>Día</th><th className="num">Conversaciones</th><th className="num">Ventas</th></tr></thead>
          <tbody>{series.filter((d) => d.conversations || d.revenue).map((d) => (
            <tr key={d.day}><td>{dayLabel(d.day)}</td><td className="num">{d.conversations}</td><td className="num">{money(d.revenue)}</td></tr>
          ))}</tbody>
        </table>
      </details>
    </section>
  );
}

/** Encuesta de satisfacción: promedio y a quién conviene llamar (calificó 1 o 2). */
function Satisfaction({ data }: { data: Insights }) {
  const s = data.satisfaction;
  return (
    <section className="results-card" aria-labelledby="csat-title">
      <h2 id="csat-title">Satisfacción de los clientes</h2>
      {s.count === 0 ? (
        <p className="muted small">
          Todavía nadie calificó. Después de pagar, el cliente puede calificar su pedido de 1 a 5 desde el chat.
        </p>
      ) : (
        <>
          <p>
            <b>{s.average?.toFixed(1)} / 5</b> promedio en {s.count} calificación{s.count === 1 ? "" : "es"} ·{" "}
            {pct(s.satisfied_rate)} conformes (4 o 5)
          </p>
          {s.unhappy.length > 0 ? (
            <>
              <h3 className="small">Para contactar ({s.unhappy.length})</h3>
              <ul className="csat-list">
                {s.unhappy.map((u) => (
                  <li key={u.order_id}>
                    <span><b>{u.score}/5</b> · pedido #{u.order_number} · {money(u.total)}</span>
                    {u.comment && <span className="muted">«{u.comment}»</span>}
                    {u.conversation_id && <a href={`#/conversaciones/${u.conversation_id}`}>Abrir conversación</a>}
                  </li>
                ))}
              </ul>
            </>
          ) : <p className="muted small">Nadie quedó insatisfecho en este período.</p>}
        </>
      )}
    </section>
  );
}
