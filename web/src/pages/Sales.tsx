import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  api,
  type ConversationRef,
  type Health,
  type MessageUI,
  type Order,
  type ProductCard,
  type SalesConversation,
  type SalesResponse,
} from "../lib/api";
import { fmtAmount } from "../lib/format";

const money = (n: number) => `$${fmtAmount(n)}`;

interface Msg {
  role: "me" | "bot";
  text: string;
  ui?: MessageUI | null;
}

const GREETING =
  "¡Hola! Soy el vendedor virtual de Sanitarios Demo C. Preguntame por canillas, duchas o repuestos y te armo el pedido.";

const SUGGESTIONS = [
  "Hola, ¿tenés canillas negras para cocina?",
  "¿Tenés canilla de lavatorio negra?",
  "Busco un flexible de 40 cm",
];

// Los links (checkout) dentro de la respuesta se muestran clickeables.
function Linkified({ text }: { text: string }) {
  const parts = text.split(/(https?:\/\/\S+)/g);
  return (
    <>
      {parts.map((p, i) =>
        /^https?:\/\//.test(p) ? (
          <a key={i} href={p} target="_blank" rel="noopener noreferrer">
            {p.includes("/sandbox/checkout/") ? "Abrir checkout de prueba" : p}
          </a>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

// Con tarjetas, las líneas "1. …" del texto sobran (el texto completo queda para canales sin
// interactividad, p. ej. un SMS).
function visibleText(m: Msg): string {
  if (!m.ui?.products?.length) return m.text;
  return m.text
    .split("\n")
    .filter((l) => !/^\d+\.\s/.test(l))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function stockLabel(c: ProductCard): { text: string; cls: string } {
  if (c.pricing_mode !== "fixed" || c.price == null) return { text: "A pedido", cls: "neu" };
  if (c.available === 0) return { text: "Sin stock", cls: "neg" };
  if (c.available === 1) return { text: "Última unidad", cls: "warn" };
  return { text: `${c.available} disponibles`, cls: "pos" };
}

function Cards({
  cards,
  onAction,
  onOpen,
  disabled,
}: {
  cards: ProductCard[];
  onAction: (message: string) => void;
  onOpen: (c: ProductCard) => void;
  disabled: boolean;
}) {
  return (
    <div className="pcards" role="list">
      {cards.map((c) => {
        const st = stockLabel(c);
        return (
          <div className="pcard" role="listitem" key={c.n}>
            <button className="pcard-img" type="button" onClick={() => onOpen(c)} aria-label={`Ver ${c.name}`}>
              {c.image_url ? <img src={c.image_url} alt="" loading="lazy" /> : <span className="noimg">Sin foto</span>}
              <span className="pcard-n">{c.n}</span>
            </button>
            <div className="pcard-body">
              <b className="pcard-name">{c.name}</b>
              {c.brand && <span className="pcard-brand">{c.brand}</span>}
              <div className="pcard-row">
                <span className="pcard-price">{c.price != null ? money(c.price) : "Consultar"}</span>
                <span className={`pill ${st.cls}`}>{st.text}</span>
              </div>
              {c.action && (
                <button
                  className="btn sm primary pcard-btn"
                  type="button"
                  disabled={disabled}
                  onClick={() => onAction(c.action!.message)}
                >
                  {c.action.label}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ProductModal({
  card,
  onClose,
  onAction,
}: {
  card: ProductCard;
  onClose: () => void;
  onAction: (message: string) => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const st = stockLabel(card);
  const specs = Object.entries(card.specs).filter(([, v]) => v != null && v !== "");
  return (
    <div className="pmodal-scrim" onClick={onClose}>
      <div className="pmodal" role="dialog" aria-modal="true" aria-label={card.name} onClick={(e) => e.stopPropagation()}>
        <button className="btn ghost sm pmodal-close" type="button" onClick={onClose} aria-label="Cerrar">
          ✕
        </button>
        {card.image_url && <img className="pmodal-img" src={card.image_url} alt={card.name} />}
        <div className="pmodal-body">
          <h2>{card.name}</h2>
          {card.brand && <span className="pcard-brand">{card.brand}</span>}
          {card.description && <p>{card.description}</p>}
          {specs.length > 0 && (
            <div className="kv">
              {specs.map(([k, v]) => (
                <div className="row" key={k}>
                  <span className="k">{k}</span>
                  <span className="v">{String(v)}</span>
                </div>
              ))}
            </div>
          )}
          <div className="pcard-row">
            <span className="pcard-price">{card.price != null ? money(card.price) : "Consultar"}</span>
            <span className={`pill ${st.cls}`}>{st.text}</span>
          </div>
          {card.action && (
            <button
              className="btn primary"
              type="button"
              onClick={() => {
                onAction(card.action!.message);
                onClose();
              }}
            >
              {card.action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/** De dónde habla el chat: la demo C (`/sandbox/sales`) o la tienda pública de un negocio. */
export interface ChatSource {
  title: string;
  subtitle: string;
  greeting: string;
  suggestions: string[];
  chat: (message: string, ref: ConversationRef | null) => Promise<SalesResponse>;
  conversation: (ref: ConversationRef) => Promise<SalesConversation>;
  /** Vista de cliente: sin datos internos (herramientas usadas, notas técnicas). */
  customerView?: boolean;
  /** Clave de sessionStorage donde la pestaña recuerda la conversación (una por tienda). */
  storageKey?: string;
}

// La referencia vive en sessionStorage: sobrevive a recargas y a ir y volver entre tiendas o del
// checkout en la misma pestaña, y se pierde al cerrarla (el token no queda en el equipo).
function loadRef(key?: string): ConversationRef | null {
  if (!key) return null;
  try {
    const v = JSON.parse(sessionStorage.getItem(key) ?? "null");
    return v && typeof v.id === "string" && typeof v.token === "string" ? { id: v.id, token: v.token } : null;
  } catch {
    return null;
  }
}

function saveRef(key: string | undefined, ref: ConversationRef | null) {
  if (!key) return;
  try {
    if (ref) sessionStorage.setItem(key, JSON.stringify(ref));
    else sessionStorage.removeItem(key);
  } catch {
    /* almacenamiento no disponible: la conversación dura lo que la vista */
  }
}

const toMsgs = (c: SalesConversation): Msg[] =>
  c.messages.map((m) => ({ role: m.role === "user" ? "me" : "bot", text: m.content, ui: m.ui }));

export const DEMO_SOURCE: ChatSource = {
  title: "Agente de ventas",
  subtitle: "Stock y precios reales del catálogo demo, carrito, pedido y link de pago. Datos sintéticos.",
  greeting: GREETING,
  suggestions: SUGGESTIONS,
  chat: api.salesChat,
  conversation: api.salesConversation,
};

export function Sales({ health, source = DEMO_SOURCE }: { health: Health | null; source?: ChatSource }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [conv, setConv] = useState<ConversationRef | null>(() => loadRef(source.storageKey));
  const [cart, setCart] = useState<Order | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [trace, setTrace] = useState<{ name: string; summary: string }[]>([]);
  const [detail, setDetail] = useState<ProductCard | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  // Generación de la conversación: "Nueva conversación" y desmontar la incrementan, y toda
  // respuesta (o error) de una generación anterior se descarta. `reads` además invalida las
  // relecturas pendientes cuando sale un mensaje, para que no pisen la respuesta más nueva.
  const gen = useRef(0);
  const reads = useRef(0);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(
    () => () => {
      gen.current++;
    },
    [],
  );

  function remember(ref: ConversationRef | null) {
    setConv(ref);
    saveRef(source.storageKey, ref);
  }

  function clearView() {
    setMessages([]);
    setCart(null);
    setOrders([]);
    setTrace([]);
    setDetail(null);
  }

  // Relee la conversación (al montar con una referencia guardada y al volver del checkout: el
  // aviso de pago lo escribe el backend). Una referencia inválida o revocada se olvida.
  function reload(ref: ConversationRef) {
    const g = gen.current;
    const r = ++reads.current;
    const current = () => g === gen.current && r === reads.current;
    source
      .conversation(ref)
      .then((c) => {
        if (!current()) return;
        setMessages(toMsgs(c));
        setCart(c.cart);
        setOrders(c.orders);
      })
      .catch((e) => {
        if (!current()) return;
        if (e instanceof ApiError && e.status === 404) {
          remember(null);
          clearView();
        }
      });
  }

  useEffect(() => {
    // Sólo al montar: después, la vista se actualiza con cada respuesta.
    if (conv) reload(conv);
  }, []);

  useEffect(() => {
    if (!conv) return;
    const refresh = () => reload(conv);
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [conv, source]);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || sending) return;
    const g = gen.current;
    reads.current++;
    setInput("");
    setMessages((m) => [...m, { role: "me", text: msg }]);
    setSending(true);
    try {
      const j = await source.chat(msg, conv);
      if (g !== gen.current) return;
      remember(j.conversation_id === conv?.id ? conv : { id: j.conversation_id, token: j.conversation_token ?? null });
      setMessages((m) => [...m, { role: "bot", text: j.reply, ui: j.ui }]);
      setCart(j.cart);
      setOrders(j.orders);
      setTrace(j.trace);
    } catch (e) {
      if (g !== gen.current) return;
      if (conv && e instanceof ApiError && e.status === 404) {
        // La conversación guardada ya no es válida: se olvida y el próximo mensaje empieza otra.
        remember(null);
        clearView();
        setMessages([
          { role: "bot", text: "Esa conversación ya no está disponible. Escribí de nuevo para empezar otra." },
        ]);
      } else {
        setMessages((m) => [
          ...m,
          { role: "bot", text: "No pude conectar con la API local. ¿Está corriendo el backend?" },
        ]);
      }
    } finally {
      if (g === gen.current) setSending(false);
    }
  }

  function restart() {
    gen.current++;
    reads.current++;
    remember(null);
    clearView();
    setSending(false);
  }

  const lastBot = messages.length && messages[messages.length - 1].role === "bot" ? messages.length - 1 : -1;

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>{source.title}</h1>
          <p className="finding">{source.subtitle}</p>
        </div>
        <div className="right">
          {!source.customerView && (
          <span className="statusline">
            <span className={`sdot ${health?.db.reachable ? "ok" : "off"}`} />
            {health
              ? `pagos: ${health.payments?.provider ?? "?"} · ${health.llm.mode === "live" ? `IA: ${health.llm.model}` : "reglas (sin IA)"}`
              : "API no disponible"}
          </span>
          )}
          <button className="btn sm" type="button" onClick={restart}>
            Nueva conversación
          </button>
        </div>
      </div>

      <div className="chat-grid">
        <section className="chatcol" aria-label="Conversación">
          <div className="chatlog" ref={logRef}>
            <div className="bubble bot">{source.greeting}</div>
            {messages.length === 0 && (
              <div className="suggest">
                <span className="suggest-label">Probá con:</span>
                {source.suggestions.map((s) => (
                  <button key={s} type="button" className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role === "me" ? "me" : "bot"}`}>
                {visibleText(m) && (
                  <div className={`bubble ${m.role === "me" ? "me" : "bot"}`}>
                    <Linkified text={m.ui?.payment ? visibleText(m).replace(m.ui.payment.url, "").trim() : visibleText(m)} />
                  </div>
                )}
                {m.ui?.products && m.ui.products.length > 0 && (
                  <Cards cards={m.ui.products} onAction={send} onOpen={setDetail} disabled={sending} />
                )}
                {m.ui?.payment && (
                  <a className="btn primary paybtn" href={m.ui.payment.url} target="_blank" rel="noopener noreferrer">
                    {m.ui.payment.provider === "simulated" ? "Pagar (prueba, no cobra)" : "Pagar con Mercado Pago"}
                  </a>
                )}
                {i === lastBot && !sending && m.ui?.quick_replies && (
                  <div className="quick">
                    {m.ui.quick_replies.map((q) => (
                      <button key={q.label} type="button" className="chip" onClick={() => send(q.message)}>
                        {q.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {sending && <div className="bubble bot typing">Escribiendo…</div>}
          </div>

          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              type="text"
              autoComplete="off"
              placeholder="Escribí como cliente…"
              aria-label="Mensaje"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="btn primary" type="submit" disabled={sending || !input.trim()}>
              Enviar
            </button>
          </form>
          {!source.customerView && (
            <p className="note">
              Canal simulado. El pago se confirma sólo con el aviso del proveedor; en modo simulado no
              se cobra nada.
            </p>
          )}
        </section>

        <aside className="rail" aria-label="Carrito y pedidos">
          <div>
            <h2 className="panel-title">Carrito</h2>
            {cart && cart.items.length ? (
              <div className="kv">
                {cart.items.map((it) => (
                  <div className="row" key={it.item_id}>
                    <span className="k">
                      {it.qty} × {it.name}
                    </span>
                    <span className="v">{money(it.line_total)}</span>
                  </div>
                ))}
                <div className="row">
                  <span className="k">Total</span>
                  <span className="v">{money(cart.total)}</span>
                </div>
              </div>
            ) : (
              <div className="empty-box">Vacío.</div>
            )}
          </div>
          <div>
            <h2 className="panel-title">Pedidos</h2>
            {orders.length ? (
              <div className="kv">
                {orders.map((o) => (
                  <div className="row" key={o.id}>
                    <span className="k">
                      #{o.number} · {money(o.total)}
                      {o.attention_reason && <span className="pill warn">revisión</span>}
                    </span>
                    <span className="v">
                      {o.status === "PENDING_PAYMENT" && o.payment?.checkout_url ? (
                        <a href={o.payment.checkout_url} target="_blank" rel="noopener noreferrer">
                          Pagar
                        </a>
                      ) : (
                        o.status_label
                      )}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-box">Sin pedidos.</div>
            )}
          </div>
          {!source.customerView && (
          <div>
            <h2 className="panel-title">Herramientas usadas</h2>
            <p className="panel-sub">Último turno del agente.</p>
            {trace.length ? (
              <div className="well">{trace.map((t) => `${t.name}: ${t.summary}`).join("\n")}</div>
            ) : (
              <div className="empty-box">—</div>
            )}
          </div>
          )}
        </aside>
      </div>
      {detail && <ProductModal card={detail} onClose={() => setDetail(null)} onAction={send} />}
    </div>
  );
}
