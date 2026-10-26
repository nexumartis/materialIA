import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type Order } from "../lib/api";
import { fmtAmount } from "../lib/format";

// Avance operativo que hace el negocio (igual que FULFILLMENT_NEXT en el backend).
const NEXT: Record<string, { status: string; label: string }[]> = {
  PAID: [{ status: "PREPARING", label: "En preparación" }, { status: "DISPATCHED", label: "Despachado" }],
  PREPARING: [{ status: "DISPATCHED", label: "Despachado" }],
  DISPATCHED: [{ status: "IN_TRANSIT", label: "En camino" }, { status: "DELIVERED", label: "Entregado" }],
  IN_TRANSIT: [{ status: "DELIVERED", label: "Entregado" }],
};

const ATTENTION: Record<string, string> = {
  paid_without_stock: "Pagado sin stock: devolver o reemplazar",
  amount_mismatch: "El monto pagado no coincide",
  duplicate_payment: "Pago duplicado: devolver uno",
};

export function OrdersPage() {
  const [list, setList] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.orders().then(setList).catch(() => setError("No pude cargar los pedidos."));
  }, []);
  useEffect(load, [load]);

  async function advance(o: Order, status: string) {
    try {
      const updated = await api.advanceOrder(o.id, status);
      setList((l) => l?.map((x) => (x.id === o.id ? updated : x)) ?? null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No pude actualizar el pedido.");
    }
  }

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Pedidos</h1>
          <p className="finding">Pedidos confirmados por tus clientes. Un pedido figura pagado sólo con el aviso verificado del medio de pago.</p>
        </div>
        <div className="right">
          <button className="btn sm" type="button" onClick={load}>Actualizar</button>
        </div>
      </div>
      {error && <div className="state err" role="alert">{error}</div>}
      {list === null ? (
        <div className="state">Cargando…</div>
      ) : list.length === 0 ? (
        <div className="empty-box">Todavía no hay pedidos. Compartí el link de tu tienda desde “Mi agente”.</div>
      ) : (
        <div className="orders">
          {list.map((o) => (
            <div className="orow" key={o.id}>
              <div>
                <b>#{o.number}</b> <span className="muted">${fmtAmount(o.total)}</span>
                <div className="muted small">{o.items.map((i) => `${i.qty} × ${i.name}`).join(", ")}</div>
              </div>
              <div className="ostate">
                <span className={`pill ${o.status === "PENDING_PAYMENT" ? "warn" : o.status === "CANCELLED" ? "neg" : "pos"}`}>
                  {o.status_label}
                </span>
                {o.attention_reason && <span className="pill neg">{ATTENTION[o.attention_reason] ?? "Revisar"}</span>}
              </div>
              <div className="cactions">
                {(NEXT[o.status] ?? []).map((n) => (
                  <button key={n.status} className="btn sm" type="button" onClick={() => void advance(o, n.status)}>
                    {n.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
