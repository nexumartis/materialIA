import { useCallback, useEffect, useMemo, useState } from "react";
import { PageHeader } from "../components/ui";
import { WeekStrip } from "../components/agenda/WeekStrip";
import { PendingQueue } from "../components/agenda/PendingQueue";
import { DayBoard } from "../components/agenda/DayBoard";
import { SlotsSettings } from "../components/agenda/SlotsSettings";
import { apptDay, errText } from "../components/agenda/shared";
import { api, type Appointment, type Deliveries as Board } from "../lib/api";
import { localDay, shiftDay } from "../lib/format";
import { useSession } from "../lib/session";

const REFRESH_MS = 60_000;

/** Días entre dos fechas YYYY-MM-DD (a mediodía, sin saltos por cambio de hora). */
const daysBetween = (a: string, b: string) =>
  Math.round((new Date(`${b}T12:00:00`).getTime() - new Date(`${a}T12:00:00`).getTime()) / 86_400_000);

/** Agenda: turnos, entregas e instalaciones en un solo lugar. Lo que falta agendar arriba, el día abajo. */
export function Agenda() {
  const { me } = useSession();
  const today = localDay();
  const [start, setStart] = useState(today);
  const [day, setDay] = useState(today);
  const [boards, setBoards] = useState<Record<string, Board>>({});
  const [appts, setAppts] = useState<Appointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const week = useMemo(() => Array.from({ length: 7 }, (_, i) => shiftDay(start, i)), [start]);

  const load = useCallback(() => {
    // Una lectura por día de la semana visible: el tablero trae las entregas del día y el cupo usado.
    Promise.all(week.map((d) => api.deliveries(d))).then(
      (list) => { setBoards(Object.fromEntries(list.map((b) => [b.date, b]))); setError(null); },
      (e) => setError(errText(e, "No pude cargar la agenda.")));
    api.appointments().then(setAppts, (e) => setError(errText(e, "No pude cargar los turnos.")));
  }, [week]);

  useEffect(() => {
    load();
    const t = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(t);
  }, [load]);

  /** Ir a un día: si cae fuera de la semana visible, se mueve la semana (en bloques desde hoy). */
  const goTo = useCallback((d: string) => {
    setDay(d);
    const off = daysBetween(start, d);
    if (off < 0 || off > 6) setStart(shiftDay(today, Math.floor(daysBetween(today, d) / 7) * 7));
  }, [start, today]);

  const counts = useMemo(() => Object.fromEntries(week.map((d) => {
    const jobs = boards[d]?.jobs.filter((j) => j.status !== "cancelled").length;
    const turns = appts?.filter((a) => apptDay(a) === d).length;
    return [d, jobs === undefined || turns === undefined ? null : jobs + turns];
  })) as Record<string, number | null>, [week, boards, appts]);

  const board = boards[day] ?? null;
  const dayAppts = useMemo(() => (appts ?? []).filter((a) => apptDay(a) === day), [appts, day]);
  const anyBoard = board ?? Object.values(boards)[0] ?? null;

  return (
    <div className="sheet">
      <PageHeader title="Agenda"
        description="Turnos, entregas e instalaciones. El agente agenda solo cuando el cliente elige día en el chat; acá ves el día y resolvés lo que falta." />
      {error && (
        <p className="state err" role="alert">
          {error}{" "}
          <button className="btn sm" type="button" onClick={load}>Reintentar</button>
        </p>
      )}
      {anyBoard && anyBoard.pending.length > 0 && (
        <PendingQueue board={anyBoard} onScheduled={(d) => { goTo(d); load(); }} />
      )}
      <WeekStrip days={week} day={day} today={today} counts={counts} onSelect={setDay}
        onShift={(n) => { const s = shiftDay(start, n * 7); setStart(s); setDay(s); }}
        onToday={() => { setStart(today); setDay(today); }} />
      {!board || !appts ? (!error && <div className="state">Cargando…</div>) : (
        <DayBoard board={board} appts={dayAppts} onChanged={load} onError={setError} />
      )}
      {me?.role === "owner" && anyBoard && (
        <SlotsSettings config={anyBoard.slots} onSaved={load} />
      )}
    </div>
  );
}
