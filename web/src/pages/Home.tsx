import { useEffect, useState } from "react";
import { ArrowUpRight, Clock, MessagesSquare, ShoppingBag, TrendingDown, TrendingUp } from "lucide-react";
import { DotBars, DotMatrix } from "../components/DotChart";
import { api, type Insights, type Order } from "../lib/api";
import { fmtAmount } from "../lib/format";
import { useSession } from "../lib/session";

const DAY_MS = 86_400_000;
const PAID = ["PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"];
const money = (n: number) => `$${fmtAmount(Math.round(n))}`;
const iso = (d: Date) => d.toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
const short = (s: string) => new Date(`${s}T12:00:00`).toLocaleDateString("es-AR", { day: "numeric", month: "short" });

function Delta({ now, before, unit }: { now: number; before: number; unit: string }) {
  if (!before && !now) return <span className="muted small">Sin movimiento {unit}</span>;
  const pct = before ? ((now - before) / before) * 100 : 100;
  const up = pct >= 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span className={`delta ${up ? "up" : "down"}`}>
      <Icon size={14} strokeWidth={2} aria-hidden /> {up ? "+" : ""}{pct.toFixed(1)}%<span className="muted"> {unit}</span>
    </span>
  );
}

/** Inicio del dueño: lo esencial del negocio de un vistazo, con datos reales (sin proyecciones). */
export function Home() {
  const { me } = useSession();
  const [data, setData] = useState<Insights | null>(null);
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [loadedAt, setLoadedAt] = useState(Date.now());
  const [now, setNow] = useState(Date.now());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () => Promise.all([api.insights(30), api.orders()]).then(([i, o]) => {
      setData(i); setOrders(o); setLoadedAt(Date.now());
    }, (e) => setError(e instanceof Error ? e.message : "No pude cargar el inicio."));
    void load();
    const reload = window.setInterval(load, 60_000);
    const tick = window.setInterval(() => setNow(Date.now()), 5_000);
    return () => { window.clearInterval(reload); window.clearInterval(tick); };
  }, []);

  const secs = Math.max(0, Math.round((now - loadedAt) / 1000));
  const updated = secs < 60 ? `hace ${secs} s` : `hace ${Math.round(secs / 60)} min`;

  return (
    <div className="home">
      <header className="home-head">
        <h1>Hola de nuevo{me?.business_name ? `, ${me.business_name.split(" (")[0]}` : ""}</h1>
        <p className="muted"><Clock size={13} strokeWidth={1.8} aria-hidden /> Actualizado {updated}</p>
      </header>
      {error && <p className="state err" role="alert">{error}</p>}
      {!data || !orders ? (!error && <div className="state">Cargando…</div>) : <Body data={data} orders={orders} />}
    </div>
  );
}

function Body({ data, orders }: { data: Insights; orders: Order[] }) {
  const today = new Date();
  const last14 = Array.from({ length: 14 }, (_, i) => iso(new Date(today.getTime() - (13 - i) * DAY_MS)));
  const paid = orders.filter((o) => PAID.includes(o.status) && o.paid_at);
  const paidPerDay = last14.map((d) => paid.filter((o) => iso(new Date(o.paid_at!)) === d).length);
  const week = paidPerDay.slice(7).reduce((a, b) => a + b, 0);
  const prevWeek = paidPerDay.slice(0, 7).reduce((a, b) => a + b, 0);

  const series = data.series;
  const conv14 = series.slice(-14).map((d) => d.conversations);
  const convWeek = conv14.slice(7).reduce((a, b) => a + b, 0);
  const convPrev = conv14.slice(0, 7).reduce((a, b) => a + b, 0);

  const pending = orders.filter((o) => o.status === "PENDING_PAYMENT" || o.status === "DEPOSIT_PAID");
  const due = pending.reduce((n, o) => n + (o.amount_due ?? o.total), 0);

  // Matriz: los días del período y, hasta fin de mes, columnas vacías (no se inventa el futuro).
  // En pantallas chicas, menos días: los puntos tienen que seguir siendo legibles.
  const narrow = typeof window !== "undefined" && window.matchMedia("(max-width: 640px)").matches;
  const past = narrow ? 10 : 21;
  const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  const future = Math.min(narrow ? 4 : 31, Math.max(0, Math.round((end.getTime() - today.getTime()) / DAY_MS)));
  const days = [
    ...series.slice(-past).map((d) => ({ label: short(d.day), value: d.revenue, conversations: d.conversations })),
    ...Array.from({ length: future }, (_, i) => ({ label: short(iso(new Date(today.getTime() + (i + 1) * DAY_MS))), value: 0, conversations: 0 })),
  ];
  const todayIndex = Math.min(series.length, past) - 1;
  const sum = (xs: { revenue: number }[]) => xs.reduce((n, d) => n + d.revenue, 0);
  const rev7 = sum(series.slice(-7)), revPrev7 = sum(series.slice(-14, -7));

  const recent = orders.filter((o) => o.status !== "CART_OPEN").slice(0, 6);

  return (
    <>
      <div className="home-kpis">
        <article className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-icon violet"><ShoppingBag size={16} strokeWidth={1.8} aria-hidden /></span>
            <h2>Pedidos pagados esta semana</h2>
            <a href="#/pedidos" className="kpi-link" aria-label="Ver pedidos"><ArrowUpRight size={16} strokeWidth={1.8} /></a>
          </div>
          <div className="kpi-body">
            <div><div className="kpi-n">{week}</div><Delta now={week} before={prevWeek} unit="vs semana pasada" /></div>
            <DotBars values={paidPerDay} labels={last14.map(short)} color="var(--dot-violet)" label={`Pedidos pagados por día, últimos 14 días: ${paidPerDay.join(", ")}`} />
          </div>
        </article>
        <article className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-icon orange"><MessagesSquare size={16} strokeWidth={1.8} aria-hidden /></span>
            <h2>Conversaciones esta semana</h2>
            <a href="#/conversaciones" className="kpi-link" aria-label="Ver conversaciones"><ArrowUpRight size={16} strokeWidth={1.8} /></a>
          </div>
          <div className="kpi-body">
            <div><div className="kpi-n">{convWeek}</div><Delta now={convWeek} before={convPrev} unit="vs semana pasada" /></div>
            <DotBars values={conv14} labels={series.slice(-14).map((d) => short(d.day))} color="var(--accent)" label={`Conversaciones por día, últimos 14 días: ${conv14.join(", ")}`} />
          </div>
        </article>
        <article className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-icon amber"><Clock size={16} strokeWidth={1.8} aria-hidden /></span>
            <h2>Esperando pago</h2>
            <a href="#/pedidos" className="kpi-link" aria-label="Ver pedidos pendientes"><ArrowUpRight size={16} strokeWidth={1.8} /></a>
          </div>
          <div className="kpi-body">
            <div><div className="kpi-n">{pending.length}</div><span className="muted small">{money(due)} por cobrar</span></div>
          </div>
        </article>
      </div>

      <section className="revenue-card" aria-labelledby="rev-title">
        <div className="rev-head">
          <div>
            <h2 id="rev-title">Ventas cobradas</h2>
            <div className="rev-n">{money(data.sales.revenue)} <span className="muted small">en 30 días</span></div>
            <Delta now={rev7} before={revPrev7} unit="últimos 7 días vs 7 anteriores" />
          </div>
          <div className="rev-side">
            <span className="pill-soft">Conversión <b>{data.conversion == null ? "—" : `${Math.round(data.conversion * 100)}%`}</b></span>
            <ul className="legend" aria-label="Referencias">
              <li><i style={{ background: "#3ccf6a" }} /> Días fuertes</li>
              <li><i style={{ background: "#f08a24" }} /> Medios</li>
              <li><i style={{ background: "#f2c94c" }} /> Bajos</li>
              <li><i style={{ background: "var(--dot-off)" }} /> Sin datos aún</li>
            </ul>
          </div>
        </div>
        <DotMatrix days={days} todayIndex={todayIndex} money={money} />
      </section>

      <section className="recent-card" aria-labelledby="recent-title">
        <div className="recent-head">
          <h2 id="recent-title">Últimos pedidos</h2>
          <a href="#/pedidos" className="btn sm">Ver todos</a>
        </div>
        {recent.length === 0 ? <p className="muted small">Todavía no hay pedidos.</p> : (
          <div className="recent-scroll">
            <table className="recent-table">
              <thead><tr><th>Pedido</th><th>Producto</th><th className="num">Total</th><th>Estado</th></tr></thead>
              <tbody>{recent.map((o) => (
                <tr key={o.id}>
                  <td><b>#{o.number}</b></td>
                  <td>{o.items[0] ? `${o.items[0].qty} × ${o.items[0].name}` : "—"}
                    {o.items.length > 1 && <span className="muted"> +{o.items.length - 1}</span>}</td>
                  <td className="num">{money(o.total)}</td>
                  <td><span className={`status-dot s-${PAID.includes(o.status) ? "ok" : o.status === "CANCELLED" || o.status === "REFUNDED" ? "bad" : "wait"}`}>{o.status_label}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
