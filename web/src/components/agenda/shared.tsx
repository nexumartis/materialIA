import type { BadgeTone } from "../ui";
import type { Appointment, Deliveries, DeliveryStatus, DeliveryWindow } from "../../lib/api";

export const DELIVERY_TONE: Record<DeliveryStatus, BadgeTone> = {
  scheduled: "neu", on_the_way: "info", arrived: "info", done: "pos", failed: "neg", cancelled: "neu",
};

/** Nombre corto de quien reparte: la parte del email antes de la arroba. */
export const personName = (email: string | null) => (email ? email.split("@")[0] : "—");

export const errText = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

/** Franjas tal como las ve el dueño: nombre corto + horario. */
export const WINDOW_NAME: Record<DeliveryWindow, { name: string; hours: string }> = {
  am: { name: "Mañana", hours: "8 a 13 h" },
  pm: { name: "Tarde", hours: "13 a 18 h" },
  day: { name: "Todo el día", hours: "8 a 18 h" },
};

/** Días de reparto del backend: 0 = lunes … 6 = domingo. */
export const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"] as const;
export const WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"] as const;

const TZ = "America/Argentina/Buenos_Aires";
/** Día YYYY-MM-DD de un turno, en hora argentina. */
export const apptDay = (a: Appointment) => new Date(a.starts_at).toLocaleDateString("en-CA", { timeZone: TZ });
export const hhmm = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: TZ });
/** Los turnos van a la columna de la mañana si empiezan antes de las 13. */
export const apptWindow = (a: Appointment): DeliveryWindow => (Number(hhmm(a.starts_at).slice(0, 2)) < 13 ? "am" : "pm");

/** Quienes pueden salir a repartir; el repartidor primero. */
export function DriverOptions({ board }: { board: Deliveries }) {
  return (
    <>
      {board.drivers.map((d) => (
        <option key={d.user_id} value={d.user_id}>
          {personName(d.email)}{d.role === "driver" ? "" : d.role === "owner" ? " (dueño)" : " (equipo)"}
        </option>
      ))}
    </>
  );
}

/** Si hay un solo repartidor, va él por defecto; si hay varios (o ninguno), queda sin asignar. */
export function defaultDriver(board: Deliveries): string {
  const drivers = board.drivers.filter((d) => d.role === "driver");
  return drivers.length === 1 ? drivers[0].user_id : "";
}
