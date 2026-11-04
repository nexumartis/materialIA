import { CalendarDays } from "lucide-react";
import { EmptyState } from "../ui";
import type { Appointment, Deliveries, DeliveryWindow } from "../../lib/api";
import { dayLabel } from "../../lib/format";
import { AppointmentCard, JobCard } from "./Cards";
import { WINDOW_NAME, apptWindow } from "./shared";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** El día elegido, en columnas por franja: turnos (con hora) y entregas e instalaciones. */
export function DayBoard({ board, appts, onChanged, onError }: {
  board: Deliveries; appts: Appointment[]; onChanged: () => void; onError: (msg: string) => void;
}) {
  const jobs = board.jobs.filter((j) => j.status !== "cancelled");
  const { slots, load } = board;
  const windows: DeliveryWindow[] = ["am", "pm"];
  if (jobs.some((j) => j.window === "day") || (slots.enabled && slots.windows.includes("day"))) windows.push("day");
  const sortedAppts = [...appts].sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  const summary = [
    jobs.length > 0 && plural(jobs.length, "entrega o instalación", "entregas o instalaciones"),
    appts.length > 0 && plural(appts.length, "turno", "turnos"),
  ].filter(Boolean).join(" · ");

  return (
    <section className="ag-dayview" aria-labelledby="ag-day-title">
      <header className="ag-day-head">
        <h2 id="ag-day-title">{dayLabel(board.date)}</h2>
        <span className="muted small">{summary || "Sin nada agendado"}</span>
      </header>
      {jobs.length === 0 && appts.length === 0 ? (
        <EmptyState icon={CalendarDays} title="Día libre">
          Acá aparecen las entregas e instalaciones (las que agendás vos y las que el cliente eligió en el chat) y los
          turnos que reservan los clientes. Si hay pedidos en «Falta agendar», elegí su día arriba.
        </EmptyState>
      ) : (
        <div className="ag-cols">
          {windows.map((w) => {
            const wa = sortedAppts.filter((a) => apptWindow(a) === w);
            const wj = jobs.filter((j) => j.window === w);
            const used = load[w] ?? 0;
            const showCap = slots.enabled && slots.windows.includes(w);
            return (
              <section key={w} className="ag-col" aria-label={`${WINDOW_NAME[w].name}, ${WINDOW_NAME[w].hours}`}>
                <header className="ag-col-head">
                  <h3>{WINDOW_NAME[w].name} <span className="muted">· {WINDOW_NAME[w].hours}</span></h3>
                  {showCap && (
                    <span className={`ag-cap${used >= slots.capacity ? " full" : ""}`}>
                      {used} de {slots.capacity} lugares{used >= slots.capacity ? " · completo" : ""}
                    </span>
                  )}
                </header>
                {wa.length === 0 && wj.length === 0 ? (
                  <p className="ag-col-empty muted small">Nada en esta franja.</p>
                ) : (
                  <ul className="ag-cards">
                    {wa.map((a) => <AppointmentCard key={a.id} appt={a} onChanged={onChanged} onError={onError} />)}
                    {wj.map((j) => <JobCard key={j.id} job={j} board={board} onChanged={onChanged} />)}
                  </ul>
                )}
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}
