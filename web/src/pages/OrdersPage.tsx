import { Fragment, useCallback, useEffect, useState } from "react";
import { Download, Eye, FileText, Landmark, Receipt, RefreshCw, ShoppingBag, Truck } from "lucide-react";
import { Badge, EmptyState, PageHeader, Stats, type Stat } from "../components/ui";
import { ApiError, api, type Carrier, type DocField, type Order, type PaymentDocument } from "../lib/api";
import { useSession } from "../lib/session";
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

const CARRIERS: { id: Carrier; label: string }[] = [
  { id: "andreani", label: "Andreani" },
  { id: "oca", label: "OCA" },
  { id: "correo_argentino", label: "Correo Argentino" },
  { id: "otro", label: "Otro" },
];
const carrierLabel = (o: Order) =>
  o.carrier === "otro" ? o.carrier_name || "correo" : CARRIERS.find((c) => c.id === o.carrier)?.label ?? o.carrier_name ?? "correo";

const WINDOW: Record<string, string> = { am: "de 8 a 13 h", pm: "de 13 a 18 h", day: "durante el día" };
/** «jueves 6/11, de 8 a 13 h»: la fecha AAAA-MM-DD es un día local, sin hora. */
function deliveryText(date: string, window?: string | null): string {
  const [y, m, d] = date.split("-").map(Number);
  const day = new Date(y, m - 1, d).toLocaleDateString("es-AR", { weekday: "long" });
  const w = window ? WINDOW[window] : undefined;
  return `${day} ${d}/${m}${w ? `, ${w}` : ""}`;
}

const canShip = (o: Order) => o.delivery_method === "delivery" && (o.status === "PAID" || o.status === "PREPARING") && !o.tracking_code;

const canConfirm = (o: Order) => o.status === "PENDING_PAYMENT" || o.status === "DEPOSIT_PAID" || o.status === "CANCELLED";

export function OrdersPage() {
  const [onlyDeposited, setOnlyDeposited] = useState(false);
  const [list, setList] = useState<Order[] | null>(null);
  const [docs, setDocs] = useState<PaymentDocument[]>([]);
  const [month, setMonth] = useState(currentMonth);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [dispatching, setDispatching] = useState<string | null>(null);
  const { me } = useSession();
  const correo = me?.modules?.correo !== false;

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

  const paidStates = ["PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"];
  // Pedidos señados: lo que falta cobrar (el saldo). Sólo se acredita con pago verificado o transferencia cotejada.
  const deposited = (list ?? []).filter((o) => o.status === "DEPOSIT_PAID");
  const balanceDue = deposited.reduce((n, o) => n + (o.amount_due ?? 0), 0);
  const shown = onlyDeposited ? deposited : list ?? [];
  const stats: Stat[] = list ? [
    { label: "Esperando el pago", value: list.filter((o) => o.status === "PENDING_PAYMENT").length },
    { label: "Pagados sin despachar", value: list.filter((o) => o.status === "PAID").length },
    { label: "Para revisar", value: list.filter((o) => o.attention_reason).length,
      tone: list.some((o) => o.attention_reason) ? "neg" : undefined },
    ...(deposited.length ? [{ label: "Saldos por cobrar", value: `$${fmtAmount(balanceDue)}`,
      hint: `${deposited.length} pedido${deposited.length === 1 ? "" : "s"} señado${deposited.length === 1 ? "" : "s"}` }] : []),
    { label: "Vendido (ARS)", value: `$${fmtAmount(list.filter((o) => paidStates.includes(o.status) && o.currency === "ARS")
        .reduce((n, o) => n + o.total, 0))}`, hint: "pedidos pagados del listado" },
  ] : [];

  return (
    <div className="sheet">
      <PageHeader
        title="Pedidos"
        description="Un pedido figura pagado sólo con el aviso verificado del medio de pago o con una transferencia que vos confirmás después de verla en tu banco. Un comprobante del cliente no alcanza."
        actions={
          <button className="btn" type="button" onClick={load}>
            <RefreshCw size={15} strokeWidth={1.8} aria-hidden /> Actualizar
          </button>
        }
      />
      {error && <div className="state err" role="alert">{error}</div>}
      {list === null ? (
        <div className="tablewrap" aria-busy="true" aria-label="Cargando pedidos">
          {[0, 1, 2].map((k) => <div className="skel-row" key={k}><span className="skel" style={{ width: "35%" }} /></div>)}
        </div>
      ) : list.length === 0 ? (
        <EmptyState icon={ShoppingBag} title="Todavía no hay pedidos">
          Compartí el link de tu tienda desde «Mi agente».
        </EmptyState>
      ) : (
        <>
          <Stats label="Resumen de pedidos" items={stats} />
          {deposited.length > 0 && (
            <div className="results-range" role="group" aria-label="Filtro de pedidos" style={{ margin: "8px 0" }}>
              <button type="button" className="chip" aria-pressed={!onlyDeposited} onClick={() => setOnlyDeposited(false)}>Todos</button>
              <button type="button" className="chip" aria-pressed={onlyDeposited} onClick={() => setOnlyDeposited(true)}>
                Señados, falta el saldo ({deposited.length})
              </button>
            </div>
          )}
          <div className="tablewrap">
            <table className="orders stack">
              <thead>
                <tr>
                  <th>Pedido</th>
                  <th className="num">Total</th>
                  <th>Estado</th>
                  <th><span className="sr">Acciones</span></th>
                </tr>
              </thead>
              <tbody>
                {shown.map((o) => (
                  <Fragment key={o.id}>
                    <tr className={confirming === o.id ? "selected" : ""} data-order={o.number}>
                      <td className="pedido">
                        <b>#{o.number}</b>
                        <small>{o.items.map((i) => `${i.qty} × ${i.name}`).join(", ")}</small>
                        {o.delivery_method && (
                          <small className="order-delivery">
                            {o.delivery_method === "pickup" ? "Retira en el local"
                              : `Envío a ${o.delivery_address?.texto ?? `${o.delivery_address?.calle ?? ""} ${o.delivery_address?.altura ?? ""}`}`}
                            {o.delivery_contact && ` · ${o.delivery_contact.name || "Sin nombre"} ${o.delivery_contact.phone}`}
                            {o.shipping ? ` · envío $${fmtAmount(o.shipping)}` : o.delivery_note ? ` · ${o.delivery_note}` : ""}
                          </small>
                        )}
                        {o.delivery_date && (
                          <small className="order-delivery">Entrega: {deliveryText(o.delivery_date, o.delivery_window)}</small>
                        )}
                        {o.tracking_code && (
                          <small className="order-ship">
                            Despachado por {carrierLabel(o)} · N° {o.tracking_url
                              ? <a href={o.tracking_url} target="_blank" rel="noopener noreferrer">{o.tracking_code}<span className="sr"> (abre el seguimiento en otra pestaña)</span></a>
                              : o.tracking_code}
                          </small>
                        )}
                      </td>
                      <td className="num" data-label="Total">${fmtAmount(o.total)} <span className="muted">{o.currency}</span>
                        {o.deposit != null && (
                          <small className="muted" style={{ display: "block" }}>
                            Seña ${fmtAmount(o.deposit)}{o.amount_due ? ` · cobrar ahora $${fmtAmount(o.amount_due)}` : ""}
                          </small>
                        )}
                      </td>
                      <td data-label="Estado">
                        <Badge tone={o.status === "PENDING_PAYMENT" || o.status === "DEPOSIT_PAID" ? "warn" : o.status === "CANCELLED" || o.status === "REFUNDED" ? "neg"
                          : o.status === "DELIVERED" ? "neu" : "pos"}>{o.status_label}</Badge>
                        {o.attention_reason && <Badge tone="neg">{ATTENTION[o.attention_reason] ?? "Revisar"}</Badge>}
                      </td>
                      <td className="actions-cell"><div className="row-actions">
                        {(NEXT[o.status] ?? []).map((n) => (
                          <button key={n.status} className="btn sm" type="button" onClick={() => void advance(o, n.status)}>
                            {n.label}
                          </button>
                        ))}
                        {o.receipt_id && (
                          <button className="btn sm" type="button"
                            onClick={() => void run(async () => saveBlob(await api.orderReceipt(o.id), `constancia-pedido-${o.number}.pdf`),
                              "No pude descargar la constancia.")}>
                            <FileText size={14} strokeWidth={1.8} aria-hidden /> Constancia (PDF)
                          </button>
                        )}
                        {o.status === "PENDING_PAYMENT" && (
                          <button className="btn sm ghost" type="button"
                            onClick={() => {
                              if (!window.confirm(`¿Cancelar el pedido #${o.number}? Se libera el stock apartado.`)) return;
                              void run(async () => {
                                const updated = await api.cancelOrder(o.id);
                                setList((l) => l?.map((x) => (x.id === o.id ? updated : x)) ?? null);
                              }, "No pude cancelar el pedido.");
                            }}>
                            Cancelar
                          </button>
                        )}
                        {correo && canShip(o) && dispatching !== o.id && (
                          <button className="btn sm" type="button" onClick={() => setDispatching(o.id)}>
                            <Truck size={14} strokeWidth={1.8} aria-hidden /> Despachar por correo
                          </button>
                        )}
                        {canConfirm(o) && confirming !== o.id && (
                          <button className="btn sm" type="button" onClick={() => setConfirming(o.id)}>
                            <Landmark size={14} strokeWidth={1.8} aria-hidden /> Confirmar transferencia
                          </button>
                        )}
                      </div></td>
                    </tr>
                    {dispatching === o.id && (
                      <tr className="expand">
                        <td colSpan={4}>
                          <ShipForm
                            order={o}
                            onCancel={() => setDispatching(null)}
                            onDone={(updated) => {
                              setDispatching(null);
                              setList((l) => l?.map((x) => (x.id === updated.id ? updated : x)) ?? null);
                            }}
                          />
                        </td>
                      </tr>
                    )}
                    {confirming === o.id && (
                      <tr className="expand">
                        <td colSpan={4}>
                          <TransferForm
                            order={o}
                            docs={docs.filter((d) => d.order_id === o.id && d.decision === null)}
                            onCancel={() => setConfirming(null)}
                            onDone={() => {
                              setConfirming(null);
                              load();
                            }}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="titlebar docs-head">
        <div>
          <h2 className="panel-title">Comprobantes recibidos</h2>
          <p className="panel-sub">Lo que mandaron los clientes. La lectura automática es una ayuda: verificá siempre en tu banco.</p>
        </div>
        <div className="right">
          <input className="field-select month-input" type="month" aria-label="Mes" value={month}
            onChange={(e) => e.target.value && setMonth(e.target.value)} />
          <button className="btn" type="button"
            onClick={() => void run(async () => saveBlob(await api.paymentRegister(month), `pagos-${month}.csv`),
              "No pude descargar el registro.")}>
            <Download size={15} strokeWidth={1.8} aria-hidden /> Registro del mes (CSV)
          </button>
        </div>
      </div>
      {docs.length === 0 ? (
        <EmptyState icon={Receipt} title={`Sin comprobantes en ${month}`} />
      ) : (
        <div className="tablewrap">
          <table className="docs stack">
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Recibido</th>
                <th>Lo que leyó el sistema</th>
                <th>Estado</th>
                <th><span className="sr">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} data-document={d.id}>
                  <td><b>Pedido #{d.order_number}</b></td>
                  <td className="muted" data-label="Recibido">
                    {new Date(d.received_at).toLocaleString("es-AR", { timeZone: "America/Argentina/Buenos_Aires",
                      day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="muted small-cell" data-label="Leído">
                    {d.fields
                      ? `Importe ${fieldText(d.fields.amount)} ${fieldText(d.fields.currency)} · ref. ${fieldText(d.fields.reference)} · ${fieldText(d.fields.date)}`
                      : d.error ?? "Todavía sin leer."}
                  </td>
                  <td data-label="Estado">
                    <Badge tone={d.decision === "linked" ? "pos" : d.decision === "rejected" ? "neg" : "neu"}>
                      {d.decision === "linked" ? "Asociado al pago" : d.decision === "rejected" ? "Descartado" : DOC_STATUS[d.status]}
                    </Badge>
                    {d.needs_review && d.decision === null && <Badge tone="warn">Datos dudosos</Badge>}
                  </td>
                  <td className="actions-cell"><div className="row-actions">
                    <button className="btn sm" type="button"
                      onClick={() => void run(async () => openBlob(await api.documentOriginal(d.id)), "No pude abrir el comprobante.")}>
                      <Eye size={14} strokeWidth={1.8} aria-hidden /> Ver original
                    </button>
                    {d.decision === null && (
                      <button className="btn sm ghost" type="button" onClick={() => void reject(d)}>Descartar</button>
                    )}
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
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
  const [amount, setAmount] = useState(String(order.amount_due || order.total));
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

/** El negocio despacha por su cuenta y carga el seguimiento: el cliente recibe el aviso en el chat. */
function ShipForm({ order, onCancel, onDone }: { order: Order; onCancel: () => void; onDone: (o: Order) => void }) {
  const [carrier, setCarrier] = useState<Carrier>("andreani");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clean = code.replace(/\s+/g, "");
  const valid = /^[A-Za-z0-9-]{4,60}$/.test(clean) && (carrier !== "otro" || name.trim().length > 0);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !valid) return;
    setBusy(true);
    setError(null);
    try {
      onDone(await api.shipOrder(order.id, {
        carrier, tracking_code: clean, ...(carrier === "otro" ? { carrier_name: name.trim() } : {}),
      }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pude registrar el despacho.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="setup-card ship-form" onSubmit={(e) => void submit(e)} aria-label={`Despachar el pedido #${order.number} por correo`}>
      <p className="muted">
        Cargá el número que te dio el correo. El pedido #{order.number} pasa a despachado y el cliente recibe el
        seguimiento en el chat.
      </p>
      <div className="ship-grid">
        <label className="field">
          Correo
          <select value={carrier} onChange={(e) => setCarrier(e.target.value as Carrier)}>
            {CARRIERS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </label>
        {carrier === "otro" && (
          <label className="field">
            Nombre del correo
            <input required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej.: Via Cargo" />
          </label>
        )}
        <label className="field">
          Número de seguimiento
          <input required value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off"
            placeholder="Ej.: 360002123456780" aria-describedby={`ship-hint-${order.id}`} />
          <small id={`ship-hint-${order.id}`}>Letras, números o guiones (de 4 a 60).</small>
        </label>
      </div>
      {error && <div className="state err" role="alert">{error}</div>}
      <div className="inline">
        <button className="btn primary sm" type="submit" disabled={busy || !valid}>
          {busy ? "Guardando…" : "Marcar despachado"}
        </button>
        <button className="btn sm" type="button" onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  );
}
