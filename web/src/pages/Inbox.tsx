import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type CatalogItem, type InboxConversation, type InboxFilter, type InboxItem, type InternalNote } from "../lib/api";
import { Bell, FileSignature, MessageSquareText, MessagesSquare, StickyNote } from "lucide-react";
import { useSession } from "../lib/session";
import { EmptyState } from "../components/ui";
import { notificationsOn, notificationsSupported } from "../lib/alerts";
import { fmtAmount, parseAmount } from "../lib/format";

const FILTERS: { key: InboxFilter; label: string }[] = [
  { key: "derivadas", label: "Derivadas" },
  { key: "sin_responder", label: "Sin responder" },
  { key: "mias", label: "Atendidas por mí" },
  { key: "con_pedido", label: "Con pedido" },
  { key: "todas", label: "Todas" },
];

const AUTHOR: Record<InboxConversation["messages"][number]["author"], string> = {
  cliente: "Cliente",
  agente: "Asistente virtual",
  persona: "Vos (equipo)",
};

const REASON: Record<"asked" | "quote" | "topic", string> = {
  asked: "Pidió una persona", quote: "Necesita cotización", topic: "Tema para el equipo" };

function when(iso: string): string {
  return new Date(iso).toLocaleString("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

/** Bandeja: el dueño ve las conversaciones, toma el control (el agente se pausa), responde y la devuelve. */
export function Inbox() {
  const { me } = useSession();
  const [filter, setFilter] = useState<InboxFilter>("derivadas");
  const [list, setList] = useState<InboxItem[] | null>(null);
  // «#/conversaciones/<id>» abre esa conversación (enlaces desde Resultados).
  const [selected, setSelected] = useState<string | null>(
    () => /^#\/conversaciones\/([0-9a-f-]{36})$/.exec(window.location.hash)?.[1] ?? null);
  const [conv, setConv] = useState<InboxConversation | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  // La conversación abierta AHORA: una respuesta que llega tarde de otra (sondeo o acción) se descarta,
  // así nunca se muestra una conversación mientras se escribe a otra.
  const current = useRef<string | null>(null);
  current.current = selected;

  const loadList = useCallback(() => {
    api.inbox(filter).then(setList).catch(() => setError("No pude cargar las conversaciones."));
  }, [filter]);

  const loadConv = useCallback((id: string) => {
    api.inboxConversation(id).then((c) => {
      if (current.current === id) setConv(c);
    }).catch((e) => {
      if (current.current !== id) return;
      if (e instanceof ApiError && e.status === 404) setSelected(null);
      else setError("No pude cargar la conversación.");
    });
  }, []);

  useEffect(() => {
    loadList();
    const t = window.setInterval(loadList, 10000);
    return () => window.clearInterval(t);
  }, [loadList]);

  useEffect(() => {
    setConv(null);
    if (!selected) return;
    loadConv(selected);
    // Mientras está abierta, se relee para ver lo nuevo que escribe el cliente.
    const t = window.setInterval(() => loadConv(selected), 5000);
    return () => window.clearInterval(t);
  }, [selected, loadConv]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [conv?.messages.length]);

  async function act(id: string, action: () => Promise<InboxConversation>, fallback: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await action();
      if (current.current === id) setConv(updated);
      loadList();
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : fallback);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    // Se responde a la conversación que está EN PANTALLA (no a otra seleccionada mientras cargaba).
    if (!text || !conv || conv.id !== selected) return;
    const id = conv.id;
    if (await act(id, () => api.replyConversation(id, text), "No pude enviar el mensaje.")) setDraft("");
  }

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Conversaciones</h1>
          <p className="finding">
            Lo que hablan tus clientes con el asistente. Tomá el control para responder vos: mientras la tengas, el
            asistente no contesta en esa conversación. Al terminar, devolvésela.
          </p>
        </div>
        <NotifyButton />
      </div>
      {error && <div className="state err" role="alert">{error}</div>}

      <div className={`inbox${selected ? " has-selection" : ""}`}>
        <section className="inbox-list" aria-label="Lista de conversaciones">
          <div className="quick" role="group" aria-label="Filtros">
            {FILTERS.map((f) => (
              <button key={f.key} type="button" aria-pressed={filter === f.key}
                className="chip" onClick={() => setFilter(f.key)}>
                {f.label}
              </button>
            ))}
          </div>
          {list === null ? (
            <div className="state">Cargando…</div>
          ) : list.length === 0 ? (
            <EmptyState icon={MessagesSquare} title="No hay conversaciones en este filtro" />
          ) : (
            <ul className="inbox-items">
              {list.map((c) => (
                <li key={c.id}>
                  <button type="button" className={`inbox-item${selected === c.id ? " active" : ""}`}
                    data-conversation={c.id} onClick={() => setSelected(c.id)}>
                    <span className="inbox-row">
                      <b>{c.last_order ? `Pedido #${c.last_order}` : "Cliente web"}</b>
                      <span className="muted small">{when(c.last_at)}</span>
                    </span>
                    <span className="muted small inbox-preview">{c.last_message || "—"}</span>
                    <span className="inbox-row pills">
                      {c.needs_human && <span className="pill warn">{REASON[c.needs_human_reason ?? "quote"]}</span>}
                      {c.unanswered && <span className="pill neu">Sin responder</span>}
                      {c.taken && <span className="pill pos">{c.taken_by_me ? "La atendés vos" : "Atendida"}</span>}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="inbox-detail" aria-label="Conversación">
          {!selected ? (
            <EmptyState icon={MessageSquareText} title="Elegí una conversación">
              Vas a ver los mensajes, el carrito y los pedidos del cliente.
            </EmptyState>
          ) : !conv || conv.id !== selected ? (
            <div className="state">Cargando…</div>
          ) : (
            <>
              <div className="inbox-head">
                <button className="btn sm inbox-back" type="button" onClick={() => setSelected(null)}>← Volver</button>
                <span className="muted small">Empezó el {when(conv.created_at)}</span>
                <span className="inbox-actions">
                  {conv.taken && !conv.taken_by_me ? (
                    <span className="pill pos">La atiende otra persona</span>
                  ) : conv.taken ? (
                    <button className="btn sm" type="button" disabled={busy}
                      onClick={() => void act(conv.id, () => api.releaseConversation(conv.id), "No pude devolver la conversación.")}>
                      Devolver al asistente
                    </button>
                  ) : (
                    <button className="btn primary sm" type="button" disabled={busy}
                      onClick={() => void act(conv.id, () => api.takeConversation(conv.id), "No pude tomar la conversación.")}>
                      Tomar el control
                    </button>
                  )}
                </span>
              </div>
              <p className="note" role="status">
                {conv.taken
                  ? "La atendés vos: el asistente no responde en esta conversación hasta que se la devuelvas."
                  : "La atiende el asistente virtual. Si respondés, tomás el control."}
              </p>
              {conv.needs_human && (conv.handoff_summary ? (
                <section className="handoff-card" aria-label="Resumen de la derivación">
                  <p><b>Quiere:</b> {conv.handoff_summary.quiere}</p>
                  {conv.handoff_summary.datos.length > 0 && <p><b>Dio:</b> {conv.handoff_summary.datos.join(" · ")}</p>}
                  {conv.handoff_summary.carrito.length > 0 && (
                    <p><b>Carrito:</b> {conv.handoff_summary.carrito.join(", ")}
                      {conv.handoff_summary.carrito_total != null && <> · ${fmtAmount(conv.handoff_summary.carrito_total)}</>}</p>
                  )}
                  <p><b>Falta:</b> {conv.handoff_summary.falta}</p>
                  <small className="muted">{conv.handoff_summary.by === "ia" ? "Resumen hecho con IA: revisá la charla ante la duda." : "Resumen automático."}</small>
                </section>
              ) : <p className="muted small">Preparando el resumen de la derivación…</p>)}
              <div className="chatlog inbox-log" ref={logRef}>
                {conv.messages.map((m, i) => (
                  <div key={i} className={`msg ${m.author === "cliente" ? "bot" : "me"}`}>
                    <span className="muted small">{AUTHOR[m.author]} · {when(m.at)}</span>
                    <div className={`bubble ${m.author === "cliente" ? "bot" : "me"}${m.author === "persona" ? " human" : ""}`}>
                      {m.content}
                    </div>
                  </div>
                ))}
              </div>
              <form className="composer" onSubmit={(e) => void send(e)}>
                <input type="text" aria-label="Respuesta" autoComplete="off" maxLength={2000}
                  placeholder={conv.taken ? "Escribile al cliente…" : "Escribí para tomar el control y responder…"}
                  value={draft} onChange={(e) => setDraft(e.target.value)} />
                <button className="btn primary" type="submit" disabled={busy || !draft.trim()}>Enviar</button>
              </form>
              <div className="kv inbox-orders">
                {conv.cart && conv.cart.items.length > 0 && (
                  <div className="row">
                    <span className="k">Carrito</span>
                    <span className="v">{conv.cart.items.map((i) => `${i.qty} × ${i.name}`).join(", ")}</span>
                  </div>
                )}
                {conv.orders.map((o) => (
                  <div className="row" key={o.id}>
                    <span className="k">Pedido #{o.number} · ${fmtAmount(o.total)}</span>
                    <span className="v">{o.status_label}</span>
                  </div>
                ))}
                {conv.documents.length > 0 && (
                  <div className="row">
                    <span className="k">Comprobantes</span>
                    <span className="v"><a href="#/pedidos">{conv.documents.length} · revisar en Pedidos</a></span>
                  </div>
                )}
              </div>
              <InternalNotes key={conv.id} conversationId={conv.id} initial={conv.notes} />
              {me?.role !== "staff" && (
                <QuoteForm key={`q-${conv.id}`} conversationId={conv.id}
                  onDone={() => void act(conv.id, () => api.inboxConversation(conv.id), "No pude actualizar la conversación.")} />
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

/** Activa las notificaciones de este navegador (el permiso lo tiene que pedir un clic). */
function NotifyButton() {
  const [on, setOn] = useState(notificationsOn());
  if (!notificationsSupported()) return null;
  if (on) return <div className="right"><span className="pill pos">Avisos activados en este navegador</span></div>;
  if (Notification.permission === "denied") {
    return <div className="right"><span className="muted small">Avisos bloqueados en el navegador</span></div>;
  }
  return (
    <div className="right">
      <button className="btn" type="button"
        onClick={() => void Notification.requestPermission().then((p) => setOn(p === "granted"))}>
        <Bell size={15} strokeWidth={1.8} aria-hidden /> Avisarme de derivaciones
      </button>
    </div>
  );
}

/** Notas del equipo sobre la conversación: el cliente y el asistente no las ven. */
function InternalNotes({ conversationId, initial }: { conversationId: string; initial: InternalNote[] }) {
  const [notes, setNotes] = useState(initial);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const n = await api.addNote(conversationId, text.trim());
      setNotes((prev) => [...prev, n]);
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pude guardar la nota.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="inbox-notes" aria-label="Notas internas">
      <h3><StickyNote size={14} strokeWidth={1.8} aria-hidden /> Notas internas <span className="muted small">· sólo las ve tu equipo</span></h3>
      {notes.length > 0 && (
        <ul>
          {notes.map((n) => (
            <li key={n.id}>
              <span className="muted small">{n.author} · {when(n.at)}</span>
              <p>{n.body}</p>
            </li>
          ))}
        </ul>
      )}
      <form className="composer" onSubmit={(e) => void add(e)}>
        <input type="text" aria-label="Nueva nota interna" maxLength={2000} autoComplete="off"
          placeholder="Ej.: es de obra, llamarlo mañana" value={text} onChange={(e) => setText(e.target.value)} />
        <button className="btn sm" type="submit" disabled={saving || !text.trim()}>Anotar</button>
      </form>
      {error && <p className="state err" role="alert">{error}</p>}
    </section>
  );
}

interface QuoteRow { item_id: string; qty: string; price: string }

/** Pedido a medida para productos «a pedido»: el dueño pone precio y, si quiere, una seña. El link
 *  de pago queda en la conversación; el pago se acredita sólo verificado. */
function QuoteForm({ conversationId, onDone }: { conversationId: string; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<CatalogItem[] | null>(null);
  const [rows, setRows] = useState<QuoteRow[]>([{ item_id: "", qty: "1", price: "" }]);
  const [deposit, setDeposit] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || items) return;
    api.catalog().then((all) => setItems(all.filter((i) => i.pricing_mode === "custom_quote" && i.active)),
      () => setError("No pude cargar el catálogo."));
  }, [open, items]);

  const total = rows.reduce((n, r) => n + (Number(r.qty) || 0) * (parseAmount(r.price) || 0), 0);
  const set = (k: number, patch: Partial<QuoteRow>) => setRows((rs) => rs.map((r, i) => (i === k ? { ...r, ...patch } : r)));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const lines = rows.map((r) => ({ item_id: r.item_id, qty: Number(r.qty), unit_price: parseAmount(r.price) }));
      await api.createQuote(conversationId, lines, deposit.trim() ? parseAmount(deposit) : null);
      setOpen(false);
      setRows([{ item_id: "", qty: "1", price: "" }]);
      setDeposit("");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pude armar el pedido.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button className="btn sm quote-open" type="button" onClick={() => setOpen(true)}>
        <FileSignature size={14} strokeWidth={1.8} aria-hidden /> Cotizar productos a pedido
      </button>
    );
  }
  return (
    <form className="quote-form" onSubmit={(e) => void submit(e)} aria-label="Cotizar productos a pedido">
      <h3><FileSignature size={14} strokeWidth={1.8} aria-hidden /> Pedido a medida</h3>
      {items && items.length === 0 ? (
        <p className="muted small">No tenés productos «a pedido» en el catálogo (columna <code>a_pedido = si</code>).</p>
      ) : (
        <>
          {rows.map((r, k) => (
            <div className="quote-row" key={k}>
              <select aria-label="Producto" required value={r.item_id} onChange={(e) => set(k, { item_id: e.target.value })}>
                <option value="">{items ? "Elegí un producto…" : "Cargando…"}</option>
                {items?.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
              <input aria-label="Cantidad" type="number" min={1} required value={r.qty} onChange={(e) => set(k, { qty: e.target.value })} />
              <input aria-label="Precio unitario" inputMode="decimal" required placeholder="Precio $" value={r.price}
                onChange={(e) => set(k, { price: e.target.value })} />
              {rows.length > 1 && (
                <button className="btn sm ghost" type="button" aria-label="Quitar producto"
                  onClick={() => setRows((rs) => rs.filter((_, i) => i !== k))}>×</button>
              )}
            </div>
          ))}
          <button className="btn sm ghost" type="button" onClick={() => setRows((rs) => [...rs, { item_id: "", qty: "1", price: "" }])}>
            + Otro producto
          </button>
          <label className="quote-deposit">
            Seña (opcional)
            <input inputMode="decimal" placeholder="Monto $ (vacío = sin seña)" value={deposit} onChange={(e) => setDeposit(e.target.value)} />
            {total > 0 && (
              <span className="muted small">
                Total ${fmtAmount(total)} · 30% = ${fmtAmount(Math.round(total * 0.3))}{" "}
                <button type="button" className="linkish" onClick={() => setDeposit(String(Math.round(total * 0.3)))}>usar 30%</button>
              </span>
            )}
          </label>
          <p className="muted small">
            Se le manda al cliente el resumen con el link de pago {deposit.trim() ? "de la seña; después de acreditarla, el del saldo" : "del total"}.
            Sólo se acredita con el pago verificado o una transferencia que cotejes en tu banco.
          </p>
          <div className="quote-actions">
            <button className="btn sm" type="button" onClick={() => setOpen(false)}>Cancelar</button>
            <button className="btn primary sm" type="submit" disabled={saving || !items}>Enviar al cliente</button>
          </div>
        </>
      )}
      {error && <p className="state err" role="alert">{error}</p>}
    </form>
  );
}
