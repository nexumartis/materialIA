import { useEffect, useState, type ReactNode } from "react";
import { BadgeCheck, Bell, Clock, Shirt, Store, Truck, UtensilsCrossed, Wrench } from "lucide-react";
import { Mark } from "./Mark";

type Msg = { who: "in" | "out"; text: ReactNode };
type Scene = {
  id: string; label: string; icon: typeof Wrench; store: string; time: string;
  msgs: Msg[]; delivery: string; total: string; order: string;
};

// Ejemplos ilustrativos de cómo vende el agente en distintos rubros (no son datos de clientes).
const SCENES: Scene[] = [
  {
    id: "ferreteria", label: "Ferretería", icon: Wrench, store: "Sanitarios del Sur", time: "02:47",
    msgs: [
      { who: "in", text: "¿Tenés la canilla monocomando negra para cocina?" },
      { who: "out", text: <>Sí: <b>monocomando negra mate</b>, $89.900, quedan 6. Casi todos la llevan con el flexible de 40 cm ($6.500). ¿Te armo el pedido?</> },
      { who: "in", text: "Dale, las dos. Envío a Avellaneda" },
      { who: "out", text: <>Avellaneda está en Zona Sur: envío $4.000. Total <b>$100.400</b>. Te paso el link de pago.</> },
    ],
    delivery: "Envío a Avellaneda", total: "$100.400", order: "#3764",
  },
  {
    id: "ropa", label: "Ropa", icon: Shirt, store: "Bruma Indumentaria", time: "23:12",
    msgs: [
      { who: "in", text: "Hola! ¿El buzo oversize gris lo tenés en L?" },
      { who: "out", text: <>En L queda <b>1 gris</b> ($42.000). Si preferís, en negro hay 4. ¿Te lo reservo?</> },
      { who: "in", text: "El gris. Lo paso a buscar mañana" },
      { who: "out", text: <>Listo, retiro en el local sin costo. Total <b>$42.000</b>. Acá tenés el link de pago.</> },
    ],
    delivery: "Retiro en el local", total: "$42.000", order: "#1208",
  },
  {
    id: "comida", label: "Comida", icon: UtensilsCrossed, store: "La Docena", time: "20:05",
    msgs: [
      { who: "in", text: "¿Hacen docena de empanadas para hoy?" },
      { who: "out", text: <>Sí: <b>docena surtida</b> $18.000, entregamos hasta las 23. ¿Le sumo una salsa criolla ($1.500)?</> },
      { who: "in", text: "Sí! A Palermo" },
      { who: "out", text: <>Envío a CABA $2.500. Total <b>$22.000</b>. Te mando el link para pagar.</> },
    ],
    delivery: "Envío a Palermo", total: "$22.000", order: "#4521",
  },
];

const STEP_MS = 1400;
const HOLD_MS = 3800;

function reducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Pantalla de acceso: el formulario a la izquierda y, en escritorio, el agente vendiendo en vivo
 *  en distintos rubros: atiende, recomienda, arma el pedido, coordina la entrega y cobra. */
export function AuthLayout({ children }: { children: ReactNode }) {
  const [scene, setScene] = useState(0);
  const [step, setStep] = useState(0);
  const [auto, setAuto] = useState(true);
  const s = SCENES[scene];
  const last = s.msgs.length + 1;   // mensajes + pago verificado

  useEffect(() => {
    if (reducedMotion()) { setStep(last); return; }
    if (step < last) {
      const t = window.setTimeout(() => setStep((n) => n + 1), step === 0 ? 500 : STEP_MS);
      return () => window.clearTimeout(t);
    }
    if (!auto) return;
    const t = window.setTimeout(() => { setScene((i) => (i + 1) % SCENES.length); setStep(0); }, HOLD_MS);
    return () => window.clearTimeout(t);
  }, [step, last, auto]);

  const pick = (i: number) => { setAuto(false); setScene(i); setStep(0); };
  const paid = step >= last;

  return (
    <main className="authx">
      <section className="authx-form">
        <div className="authx-brand"><Mark /> <span>Tu vendedor por chat</span></div>
        <div className="authx-inner">{children}</div>
        <p className="authx-legal muted">Tus datos y los de tus clientes quedan separados de los de cualquier otro negocio.</p>
      </section>
      <aside className="authx-side" aria-label="Cómo vende el agente">
        <div className="authx-copy">
          <h2>Del «¿tenés?» al pago acreditado.</h2>
          <p>Consulta, recomendación, carrito, entrega y link de pago en la misma charla, sin que tengas que meterte.</p>
        </div>

        <div className="authx-tabs" role="group" aria-label="Ver un ejemplo por rubro">
          {SCENES.map((x, i) => (
            <button key={x.id} type="button" aria-pressed={i === scene} onClick={() => pick(i)}>
              <x.icon size={15} strokeWidth={1.8} aria-hidden /> {x.label}
            </button>
          ))}
        </div>

        <div className="authx-stage">
          <div className={`authx-toast${paid ? " show" : ""}`} aria-hidden>
            <span className="authx-toast-i"><Bell size={15} strokeWidth={2} /></span>
            <div><b>Nueva venta · {s.total}</b><span>Pedido {s.order} cobrado a las {s.time}</span></div>
          </div>
          <div className="authx-chat" data-ui aria-hidden key={s.id}>
            <div className="authx-chat-head">
              <span className="authx-avatar"><Store size={15} strokeWidth={1.8} /></span>
              <div><b>{s.store}</b><span><i /> Agente en línea</span></div>
              <span className="authx-clock"><Clock size={13} strokeWidth={1.8} /> {s.time}</span>
            </div>
            <div className="authx-thread">
              {s.msgs.slice(0, step).map((m, i) => (
                <div key={i} className={`authx-msg ${m.who}`}>{m.text}</div>
              ))}
              {step > 0 && step < s.msgs.length && s.msgs[step].who === "out" && (
                <div className="authx-typing"><i /><i /><i /></div>
              )}
              {paid && (
                <div className="authx-paid">
                  <BadgeCheck size={16} strokeWidth={2} />
                  <span>Pago verificado · {s.order}</span>
                  <em><Truck size={13} strokeWidth={1.8} /> {s.delivery}</em>
                </div>
              )}
            </div>
          </div>
        </div>

        <ul className="authx-points">
          <li><b>Stock y precios reales</b><span>Responde sólo con lo que tenés cargado.</span></li>
          <li><b>Del chat al pedido</b><span>Carrito, entrega o retiro, y link de pago.</span></li>
          <li><b>Cobro verificado</b><span>La venta cuenta recién con el pago acreditado.</span></li>
        </ul>
      </aside>
    </main>
  );
}
