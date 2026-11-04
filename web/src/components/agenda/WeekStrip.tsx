import { ChevronLeft, ChevronRight } from "lucide-react";

const weekday = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString("es-AR", { weekday: "short" }).replace(".", "");
const dayNum = (d: string) => new Date(`${d}T12:00:00`).getDate();
const month = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString("es-AR", { month: "long" });

/** Siete días desde la semana elegida; cada uno dice cuántas cosas hay ese día. */
export function WeekStrip({ days, day, today, counts, onSelect, onShift, onToday }: {
  days: string[]; day: string; today: string; counts: Record<string, number | null>;
  onSelect: (d: string) => void; onShift: (n: number) => void; onToday: () => void;
}) {
  const range = month(days[0]) === month(days[6]) ? month(days[0]) : `${month(days[0])} – ${month(days[6])}`;
  return (
    <section className="ag-week" aria-label="Semana">
      <div className="ag-week-head">
        <h2>{range.charAt(0).toUpperCase() + range.slice(1)}</h2>
        <div className="ag-week-nav">
          {!days.includes(today) && <button className="btn sm" type="button" onClick={onToday}>Hoy</button>}
          <button className="btn icon" type="button" aria-label="Semana anterior" onClick={() => onShift(-1)}>
            <ChevronLeft size={18} strokeWidth={1.8} aria-hidden />
          </button>
          <button className="btn icon" type="button" aria-label="Semana siguiente" onClick={() => onShift(1)}>
            <ChevronRight size={18} strokeWidth={1.8} aria-hidden />
          </button>
        </div>
      </div>
      <div className="ag-days" role="group" aria-label="Elegí un día">
        {days.map((d) => {
          const n = counts[d];
          const name = d === today ? "Hoy" : weekday(d);
          return (
            <button key={d} type="button" className={`ag-day${d === today ? " today" : ""}`} aria-pressed={d === day}
              aria-label={`${name} ${dayNum(d)}${n == null ? "" : n === 0 ? ", libre" : `, ${n} agendado${n === 1 ? "" : "s"}`}`}
              onClick={() => onSelect(d)}>
              <span className="ag-day-name">{name}</span>
              <span className="ag-day-num">{dayNum(d)}</span>
              <span className="ag-day-count" aria-hidden>{n == null ? "·" : n === 0 ? "—" : n}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
