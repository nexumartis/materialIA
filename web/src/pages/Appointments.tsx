import { useCallback, useEffect, useState } from "react";
import { CalendarDays } from "lucide-react";
import { EmptyState, PageHeader } from "../components/ui";
import { api, type Appointment } from "../lib/api";

/** Próximos turnos que reservaron los clientes en el chat. */
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
        <ul className="team-list" aria-label="Próximos turnos">
          {items.map((a) => (
            <li key={a.id}>
              <span className="who"><b>{a.label}</b> · {a.service}</span>
              {a.conversation_id && <a className="btn sm" href={`#/conversaciones/${a.conversation_id}`}>Conversación</a>}
              <button className="btn sm ghost" type="button" onClick={() => void cancel(a)}>Cancelar</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
