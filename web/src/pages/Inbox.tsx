import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type InboxConversation, type InboxFilter, type InboxItem } from "../lib/api";
import { fmtAmount } from "../lib/format";

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

const REASON: Record<"asked" | "quote", string> = { asked: "Pidió una persona", quote: "Necesita cotización" };

function when(iso: string): string {
  return new Date(iso).toLocaleString("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

/** Bandeja: el dueño ve las conversaciones, toma el control (el agente se pausa), responde y la devuelve. */
export function Inbox() {
  const [filter, setFilter] = useState<InboxFilter>("derivadas");
  const [list, setList] = useState<InboxItem[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
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
      </div>
      {error && <div className="state err" role="alert">{error}</div>}

      <div className={`inbox${selected ? " has-selection" : ""}`}>
        <section className="inbox-list" aria-label="Lista de conversaciones">
          <div className="quick" role="tablist" aria-label="Filtros">
            {FILTERS.map((f) => (
              <button key={f.key} type="button" role="tab" aria-selected={filter === f.key}
                className={`chip${filter === f.key ? " on" : ""}`} onClick={() => setFilter(f.key)}>
                {f.label}
              </button>
            ))}
          </div>
          {list === null ? (
            <div className="state">Cargando…</div>
          ) : list.length === 0 ? (
            <div className="empty-box">No hay conversaciones en este filtro.</div>
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
            <div className="empty-box">Elegí una conversación.</div>
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
            </>
          )}
        </section>
      </div>
    </div>
  );
}
