import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type DocField, type Order, type PaymentDocument } from "../lib/api";
import { openBlob, saveBlob } from "../lib/download";
import { fmtAmount, parseAmount } from "../lib/format";

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

const DOC_STATUS: Record<PaymentDocument["status"], string> = {
  received: "En lectura",
  processing: "En lectura",
  read: "Leído",
  unreadable: "No se pudo leer",
};

/** Mes actual en hora argentina (AAAA-MM), el del registro. */
function currentMonth(): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Argentina/Buenos_Aires", year: "numeric", month: "2-digit" })
    .formatToParts(new Date());
  return `${parts.find((p) => p.type === "year")?.value}-${parts.find((p) => p.type === "month")?.value}`;
}

/** Lo que leyó el OCR, con su incertidumbre: un valor dudoso se muestra como candidato. */
function fieldText(f: DocField | undefined): string {
  if (!f) return "?";
  if (f.value) return f.value;
  return f.candidates.length ? `¿${f.candidates.join(" / ")}?` : "?";
}

const canConfirm = (o: Order) => o.status === "PENDING_PAYMENT" || o.status === "CANCELLED";

export function OrdersPage() {
  const [list, setList] = useState<Order[] | null>(null);
  const [docs, setDocs] = useState<PaymentDocument[]>([]);
  const [month, setMonth] = useState(currentMonth);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.orders().then(setList).catch(() => setError("No pude cargar los pedidos."));
    api.paymentDocuments(month).then(setDocs).catch(() => setError("No pude cargar los comprobantes."));
  }, [month]);
  useEffect(load, [load]);

  async function advance(o: Order, status: string) {
    try {
      const updated = await api.advanceOrder(o.id, status);
      setList((l) => l?.map((x) => (x.id === o.id ? updated : x)) ?? null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No pude actualizar el pedido.");
    }
  }

  async function run(action: () => Promise<void>, fallback: string) {
    try {
      await action();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : fallback);
    }
  }

  async function reject(d: PaymentDocument) {
    if (!window.confirm(`¿Descartar este comprobante del pedido #${d.order_number}? No cambia ningún pago.`)) return;
    await run(async () => {
      await api.rejectDocument(d.id);
      load();
    }, "No pude descartar el comprobante.");
  }

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Pedidos</h1>
          <p className="finding">
            Un pedido figura pagado sólo con el aviso verificado del medio de pago o con una transferencia que vos
            confirmás después de verla en tu banco. Un comprobante del cliente no alcanza.
          </p>
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
            <div key={o.id}>
              <div className="orow">
                <div>
                  <b>#{o.number}</b> <span className="muted">${fmtAmount(o.total)} {o.currency}</span>
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
                  {o.receipt_id && (
                    <button className="btn sm" type="button"
                      onClick={() => void run(async () => saveBlob(await api.orderReceipt(o.id), `constancia-pedido-${o.number}.pdf`),
                        "No pude descargar la constancia.")}>
                      Constancia (PDF)
                    </button>
                  )}
                  {canConfirm(o) && confirming !== o.id && (
                    <button className="btn sm" type="button" onClick={() => setConfirming(o.id)}>
                      Confirmar transferencia
                    </button>
                  )}
                </div>
              </div>
              {confirming === o.id && (
                <TransferForm
                  order={o}
                  docs={docs.filter((d) => d.order_id === o.id && d.decision === null)}
                  onCancel={() => setConfirming(null)}
                  onDone={() => {
                    setConfirming(null);
                    load();
                  }}
                />
              )}
            </div>
          ))}
        </div>
      )}

      <div className="titlebar docs-head">
        <div>
          <h2 className="panel-title">Comprobantes recibidos</h2>
          <p className="panel-sub">Lo que mandaron los clientes. La lectura automática es una ayuda: verificá siempre en tu banco.</p>
        </div>
        <div className="right inline">
          <input className="field-select" type="month" aria-label="Mes" value={month}
            onChange={(e) => e.target.value && setMonth(e.target.value)} />
          <button className="btn sm" type="button"
            onClick={() => void run(async () => saveBlob(await api.paymentRegister(month), `pagos-${month}.csv`),
              "No pude descargar el registro.")}>
            Registro del mes (CSV)
          </button>
        </div>
      </div>
      {docs.length === 0 ? (
        <div className="empty-box">Sin comprobantes en {month}.</div>
      ) : (
        <div className="orders">
          {docs.map((d) => (
            <div className="orow" key={d.id}>
              <div>
                <b>Pedido #{d.order_number}</b>{" "}
                <span className="muted">
                  {new Date(d.received_at).toLocaleString("es-AR", { timeZone: "America/Argentina/Buenos_Aires" })}
                </span>
                <div className="muted small">
                  {d.fields
                    ? `Leído: importe ${fieldText(d.fields.amount)} ${fieldText(d.fields.currency)} · referencia ${fieldText(d.fields.reference)} · fecha ${fieldText(d.fields.date)}`
                    : d.error ?? "Todavía sin leer."}
                </div>
              </div>
              <div className="ostate">
                <span className={`pill ${d.decision === "linked" ? "pos" : d.decision === "rejected" ? "neg" : "neu"}`}>
                  {d.decision === "linked" ? "Asociado al pago" : d.decision === "rejected" ? "Descartado" : DOC_STATUS[d.status]}
                </span>
                {d.needs_review && d.decision === null && <span className="pill warn">Datos dudosos</span>}
              </div>
              <div className="cactions">
                <button className="btn sm" type="button"
                  onClick={() => void run(async () => openBlob(await api.documentOriginal(d.id)), "No pude abrir el comprobante.")}>
                  Ver original
                </button>
                {d.decision === null && (
                  <button className="btn sm" type="button" onClick={() => void reject(d)}>Descartar</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** El dueño acredita lo que cotejó en su banco: referencia, importe y moneda reales. */
function TransferForm({ order, docs, onCancel, onDone }: {
  order: Order;
  docs: PaymentDocument[];
  onCancel: () => void;
  onDone: () => void;
}) {
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState(String(order.total));
  const [currency, setCurrency] = useState(order.currency);
  const [linked, setLinked] = useState<string[]>(() => docs.map((d) => d.id));
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    const value = parseAmount(amount);
    if (Number.isNaN(value) || value <= 0) {
      setResult("Importe inválido. Escribilo como en el banco, por ejemplo 12.345,50.");
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const r = await api.confirmTransfer(order.id, { reference, amount: value, currency, document_ids: linked });
      if (r.outcome === "pedido pagado" || r.outcome === "ya estaba pagado") onDone();
      else setResult(`No se acreditó: ${r.outcome}.`);
    } catch (err) {
      setResult(err instanceof ApiError ? err.message : "No pude confirmar la transferencia.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="setup-card transfer-form" onSubmit={(e) => void submit(e)}>
      <p className="muted">
        Confirmá sólo si ya viste el dinero en tu cuenta. El pedido #{order.number} pasa a pagado, se descuenta el
        stock y el cliente recibe su constancia.
      </p>
      <div className="grid3">
        <label className="field">
          Referencia de la operación
          <input required value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Nº de operación del banco" />
        </label>
        <label className="field">
          Importe acreditado
          <input required inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <label className="field">
          Moneda
          <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
            <option value="ARS">ARS</option>
            <option value="USD">USD</option>
          </select>
        </label>
      </div>
      {docs.length > 0 && (
        <div className="checks">
          {docs.map((d) => (
            <label className="check" key={d.id}>
              <input type="checkbox" checked={linked.includes(d.id)}
                onChange={(e) => setLinked((l) => (e.target.checked ? [...l, d.id] : l.filter((x) => x !== d.id)))} />
              Asociar el comprobante recibido el {new Date(d.received_at).toLocaleDateString("es-AR")}
            </label>
          ))}
        </div>
      )}
      {result && <div className="state err" role="alert">{result}</div>}
      <div className="inline">
        <button className="btn primary sm" type="submit" disabled={busy || !reference.trim()}>
          {busy ? "Confirmando…" : "Confirmar transferencia"}
        </button>
        <button className="btn sm" type="button" onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  );
}
