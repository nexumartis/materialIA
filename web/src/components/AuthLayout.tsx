import type { ReactNode } from "react";
import { BadgeCheck, MessagesSquare, PackageCheck, ShoppingCart, UserRound } from "lucide-react";
import { Mark } from "./Mark";

/** Pantalla de acceso: el formulario a la izquierda y, en escritorio, un campo de color con un
 *  fragmento real del producto (una charla del agente con stock, carrito y cobro verificado). */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="authx">
      <section className="authx-form">
        <div className="authx-brand"><Mark /> <span>Tu vendedor por chat</span></div>
        <div className="authx-inner">{children}</div>
        <p className="authx-legal muted">Tus datos y los de tus clientes quedan separados de los de cualquier otro negocio.</p>
      </section>
      <aside className="authx-side" aria-label="Qué hace el agente">
        <h2>Vende con tu stock real y cobra con pago verificado.</h2>
        <div className="authx-chat" data-ui aria-hidden>
          <div className="authx-msg in"><UserRound size={14} strokeWidth={1.8} /> ¿Tenés la canilla negra para cocina?</div>
          <div className="authx-msg out">
            Sí. <b>Canilla monocomando negra mate</b> · $89.900 · 6 disponibles. ¿Te la agrego?
          </div>
          <div className="authx-msg in"><UserRound size={14} strokeWidth={1.8} /> Dale, la compro</div>
          <div className="authx-cart">
            <ShoppingCart size={15} strokeWidth={1.8} />
            <span>1 × Canilla monocomando negra mate</span>
            <b>$89.900</b>
          </div>
          <div className="authx-paid"><BadgeCheck size={16} strokeWidth={2} /> Pago verificado · pedido #3764</div>
        </div>
        <ul className="authx-points">
          <li><PackageCheck size={18} strokeWidth={1.8} aria-hidden /> Precio y stock salen de tu catálogo: nunca inventa.</li>
          <li><BadgeCheck size={18} strokeWidth={1.8} aria-hidden /> Un pedido figura pagado sólo con el pago confirmado.</li>
          <li><MessagesSquare size={18} strokeWidth={1.8} aria-hidden /> Cuando hace falta una persona, te lo pasa con un resumen.</li>
        </ul>
      </aside>
    </main>
  );
}
