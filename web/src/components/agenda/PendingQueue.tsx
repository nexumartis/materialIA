import { useState } from "react";
import { CalendarPlus, MapPin } from "lucide-react";
import type { Deliveries, PendingDelivery } from "../../lib/api";
import { itemsText } from "../../lib/format";
import { ScheduleForm } from "./ScheduleForm";

/** «Calle 123, Lanús» → la localidad aparte, para que se lea primero a dónde hay que ir. */
export function Address({ text }: { text: string }) {
  if (!text) return <span className="muted">Sin dirección</span>;
  const i = text.lastIndexOf(", ");
  if (i < 0) return <span>{text}</span>;
  return <span><b className="ag-loc">{text.slice(i + 2)}</b> · {text.slice(0, i)}</span>;
}

/** Pedidos pagados con envío que todavía no tienen día: lo único que el dueño tiene que resolver. */
export function PendingQueue({ board, onScheduled }: { board: Deliveries; onScheduled: (date: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const n = board.pending.length;
  return (
    <section className="ag-pending" aria-labelledby="ag-pending-title">
      <header className="ag-pending-head">
        <h2 id="ag-pending-title">Falta agendar <span className="ag-n">{n}</span></h2>
        <p className="muted small">Pedidos pagados con envío a domicilio que todavía no tienen día. Al agendar, le avisamos al cliente por el chat.</p>
      </header>
      <ul className="ag-pending-list">
        {board.pending.map((p) => (
          <li key={p.order_id} className={open === p.order_id ? "open" : undefined}>
            <PendingRow p={p} />
            {open === p.order_id ? (
              <ScheduleForm board={board} order={p} onCancel={() => setOpen(null)}
                onDone={(date) => { setOpen(null); onScheduled(date); }} />
            ) : (
              <button className="btn primary sm ag-pick" type="button" onClick={() => setOpen(p.order_id)}
                aria-label={`Elegir día para el pedido #${p.order_number}`}>
                <CalendarPlus size={14} strokeWidth={1.8} aria-hidden /> Elegir día
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function PendingRow({ p }: { p: PendingDelivery }) {
  return (
    <div className="ag-order">
      <div className="ag-order-top">
        <b>Pedido #{p.order_number}</b>
        {p.contact && <span className="muted small">{p.contact}</span>}
      </div>
      <span className="small">{itemsText(p.items)}</span>
      <span className="small ag-meta">
        <MapPin size={14} strokeWidth={1.8} aria-hidden /> <Address text={p.address} />
      </span>
    </div>
  );
}
