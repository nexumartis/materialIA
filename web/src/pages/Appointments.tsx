import { useCallback, useEffect, useState } from "react";
import { CalendarDays } from "lucide-react";
import { EmptyState, PageHeader } from "../components/ui";
import { api, type Appointment } from "../lib/api";

const TZ = "America/Argentina/Buenos_Aires";
const hhmm = (iso: string) => new Date(iso).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: TZ });
const minutes = (a: Appointment) => Math.round((new Date(a.ends_at).getTime() - new Date(a.starts_at).getTime()) / 60000);
function groups(items: Appointment[]): [string, Appointment[]][] {
  const today = new Date().toLocaleDateString("en-CA", { timeZone: TZ });
  const tomorrow = new Date(Date.now() + 86_400_000).toLocaleDateString("en-CA", { timeZone: TZ });
  const map = new Map<string, Appointment[]>();
  for (const a of items) {
    const key = new Date(a.starts_at).toLocaleDateString("en-CA", { timeZone: TZ });
    map.set(key, [...(map.get(key) ?? []), a]);
  }
  return [...map.entries()].map(([key, list]) => {
    const long = new Date(`${key}T12:00:00`).toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });
    const name = key === today ? `Hoy, ${long}` : key === tomorrow ? `Mañana, ${long}` : long;
    return [name.charAt(0).toUpperCase() + name.slice(1), list];
  });
}

/** Próximos turnos que reservaron los clientes en el chat, como agenda por día. */
export function Appointments() {
  const [items, setItems] = useState<Appointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    api.appointments().then(setItems, (e) => setError(e instanceof Error ? e.message : "No pude cargar los turnos."));
  }, []);
  useEffect(load, [load]);

  async function cancel(a: Appointment) {
    if (!window.confirm(`¿Cancelar ${a.service} del ${a.label}? Avisale al cliente por el chat.`)) return;
    try {
      await api.cancelAppointment(a.id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pude cancelarlo.");
    }
  }
  return (
    <div className="sheet">
      <PageHeader title="Turnos" description="Los reservan los clientes en el chat, sólo en horarios libres. Configurá servicios y horarios en Ajustes del agente → Políticas." />
      {error && <p className="state err" role="alert">{error}</p>}
      {!items ? (!error && <div className="state">Cargando…</div>) : items.length === 0 ? (
        <EmptyState icon={CalendarDays} title="No hay turnos próximos">
          Cuando un cliente pida un turno en el chat, aparece acá.
        </EmptyState>
      ) : (
        <div className="agenda">
          {groups(items).map(([day, list]) => (
            <section key={day} className="agenda-day" aria-label={day}>
              <h2>{day} <span className="muted">{list.length} turno{list.length === 1 ? "" : "s"}</span></h2>
              <ul>
                {list.map((a) => (
                  <li key={a.id}>
                    <time className="agenda-time" dateTime={a.starts_at}>{hhmm(a.starts_at)}</time>
                    <span className="person"><b>{a.service}</b><small className="muted">{minutes(a)} min · hasta {hhmm(a.ends_at)}</small></span>
                    {a.conversation_id && <a className="btn sm ghost" href={`#/conversaciones/${a.conversation_id}`}>Ver conversación</a>}
                    <button className="btn sm ghost" type="button" onClick={() => void cancel(a)}>Cancelar</button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
