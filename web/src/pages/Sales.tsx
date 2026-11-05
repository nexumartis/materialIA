import { useEffect, useRef, useState } from "react";
import { Truck, Volume2 } from "lucide-react";
import {
  ApiError,
  api,
  type AudioCaps,
  type BuyerDocument,
  type ConversationRef,
  type Health,
  type MessageUI,
  type Order,
  type PhotoCaps,
  type PhotoDescription,
  type ProductCard,
  type SalesConversation,
  type SalesResponse,
} from "../lib/api";
import { saveBlob } from "../lib/download";
import { fmtAmount } from "../lib/format";
import { VoiceInput } from "../components/VoiceInput";
import { PhotoInput } from "../components/PhotoInput";

const money = (n: number) => `$${fmtAmount(n)}`;

const MAX_MESSAGE = 2000;

interface Msg {
  /** UUID del servidor: sólo los mensajes releídos de la conversación lo tienen. */
  id?: string;
  role: "me" | "bot";
  text: string;
  ui?: MessageUI | null;
}

const GREETING =
  "¡Hola! Soy Caro, la asistente virtual de Sanitarios Demo C. Preguntame por canillas, duchas o repuestos y te armo el pedido.";

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
              {c.variants && c.variants.length > 0 && (
                <div className="pcard-variants" aria-label="Otras variantes">
                  <span className="muted small">También en:</span>
                  {c.variants.map((v) => (
                    <button key={v.message} type="button" className="chip" disabled={disabled}
                      onClick={() => onAction(v.message)}>
                      {v.label}{v.available !== null && v.available <= 0 ? " (sin stock)" : ""}
                    </button>
                  ))}
                </div>
              )}
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
          {card.datasheet_url && (
            <a className="btn sm" href={card.datasheet_url} target="_blank" rel="noopener noreferrer">
              Ver ficha técnica (PDF)
            </a>
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
  /** Tienda pública: el comprador adjunta su comprobante y baja su constancia. */
  uploadDocument?: (ref: ConversationRef, orderId: string, file: File) => Promise<unknown>;
  receipt?: (ref: ConversationRef, receiptId: string) => Promise<Blob>;
  cancelOrder?: (ref: ConversationRef, orderId: string) => Promise<Order>;
  /** Tienda pública: el comprador califica su pedido pagado (encuesta de satisfacción). */
  rateOrder?: (ref: ConversationRef, orderId: string, score: number, comment: string) => Promise<unknown>;
  /** Tienda pública: dictar el mensaje y escuchar respuestas (si el backend lo habilita). */
  audio?: {
    caps: () => Promise<AudioCaps>;
    transcribe: (wav: Blob, ref: ConversationRef | null, signal: AbortSignal) => Promise<{ text: string }>;
    speak: (ref: ConversationRef, messageId: string) => Promise<Blob>;
  };
  /** Tienda pública: mandar una foto del producto (si el backend lo habilita). */
  photos?: {
    caps: () => Promise<PhotoCaps>;
    describe: (image: Blob, ref: ConversationRef | null, signal: AbortSignal) => Promise<PhotoDescription>;
  };
}

// Errores de la foto en criollo; el resto usa el `detail` del backend.
function photoError(e: unknown): string {
  if (!(e instanceof ApiError)) return "No pude mandar la foto. Probá de nuevo o escribí tu consulta.";
  if (e.status === 413) return "La foto es demasiado pesada. Probá con otra.";
  if (e.status === 415) return "No pude usar esa imagen. Probá con otra foto del producto o escribí tu consulta.";
  if (e.status === 429) return "Mandaste varias fotos seguidas. Esperá un ratito o escribí tu consulta.";
  if (e.status === 0) return "No pude conectar para mandar la foto. Probá de nuevo.";
  return e.message;
}

const RATEABLE = ["PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"];

const DOC_STATUS: Record<BuyerDocument["status"], string> = {
  received: "recibido, en lectura",
  processing: "recibido, en lectura",
  read: "recibido, lo revisa el negocio",
  unreadable: "no se pudo leer; lo revisa el negocio",
};

function docLabel(d: BuyerDocument): string {
  if (d.decision === "linked") return "asociado al pago confirmado";
  if (d.decision === "rejected") return "el negocio no lo tomó; consultá en el chat";
  return DOC_STATUS[d.status];
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
  c.messages.map((m) => ({ id: m.id, role: m.role === "user" ? "me" : "bot", text: m.content, ui: m.ui }));

export const DEMO_SOURCE: ChatSource = {
  title: "Agente de ventas",
  subtitle: "Stock y precios reales del catálogo demo, carrito, pedido y link de pago. Datos sintéticos.",
  greeting: GREETING,
  suggestions: SUGGESTIONS,
  chat: api.salesChat,
  conversation: api.salesConversation,
  audio: { caps: api.salesAudio, transcribe: api.salesTranscribe, speak: api.salesMessageAudio },
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
  const [documents, setDocuments] = useState<BuyerDocument[]>([]);
  const [fileNote, setFileNote] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [attended, setAttended] = useState(false);
  const [audioCaps, setAudioCaps] = useState<AudioCaps | null>(null);
  // Audio de respuestas por id de mensaje. Sin autoplay: se muestra el reproductor y el comprador le da play.
  const [voices, setVoices] = useState<Record<string, { url?: string; auto?: boolean; loading?: boolean; error?: string }>>({});
  // Notas de voz del comprador, por posición en la conversación (sobrevive a la relectura del
  // historial; por texto, dos notas iguales o un mensaje escrito igual compartirían el audio).
  const [myVoice, setMyVoice] = useState<Record<number, string>>({});
  // Fotos del comprador, igual que las notas de voz: por posición, sólo en esta sesión (la imagen
  // no se guarda; al recargar queda el mensaje de texto). Las URLs locales se liberan con las de voz.
  const [myPhoto, setMyPhoto] = useState<Record<number, { url: string; query: string | null }>>({});
  const [photoCaps, setPhotoCaps] = useState<PhotoCaps | null>(null);
  // Foto en curso («Mirando la foto…») o que no se pudo usar (con la pista local, que no va al servidor).
  const [photo, setPhoto] = useState<{ url: string; hint?: string } | null>(null);
  const [photoNote, setPhotoNote] = useState<string | null>(null);
  const photoAbort = useRef<AbortController | null>(null);
  const voiceUrls = useRef<string[]>([]);
  const [voiceKey, setVoiceKey] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
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
      photoAbort.current?.abort();
      voiceUrls.current.forEach((u) => URL.revokeObjectURL(u));
    },
    [],
  );

  useEffect(() => {
    let alive = true;
    source.photos
      ?.caps()
      .then((c) => alive && setPhotoCaps(c.enabled ? c : null))
      .catch(() => alive && setPhotoCaps(null)); // sin capacidades no aparece la cámara
    return () => {
      alive = false;
    };
  }, [source]);

  useEffect(() => {
    let alive = true;
    source.audio
      ?.caps()
      .then((c) => alive && setAudioCaps(c.enabled ? c : null))
      .catch(() => alive && setAudioCaps(null)); // sin capacidades no se muestra nada de audio
    return () => {
      alive = false;
    };
  }, [source]);

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
    setDocuments([]);
    setFileNote(null);
    setAttended(false);
    voiceUrls.current.forEach((u) => URL.revokeObjectURL(u));
    voiceUrls.current = [];
    setVoices({});
    setMyVoice({});
    setMyPhoto({});
    photoAbort.current?.abort();
    photoAbort.current = null;
    setPhoto(null);
    setPhotoNote(null);
    setVoiceKey((k) => k + 1); // descarta grabación/transcripción en curso
  }

  // Relee la conversación (al montar con una referencia guardada y al volver del checkout: el
  // aviso de pago lo escribe el backend). Una referencia inválida o revocada se olvida.
  function reload(ref: ConversationRef, speak = false) {
    const g = gen.current;
    const r = ++reads.current;
    const current = () => g === gen.current && r === reads.current;
    source
      .conversation(ref)
      .then((c) => {
        if (!current()) return;
        const msgs = toMsgs(c);
        setMessages(msgs);
        // El comprador habló: Caro le contesta también con su voz.
        const last = speak ? [...msgs].reverse().find((m) => m.role === "bot" && m.id) : undefined;
        if (last?.id && audioCaps && last.text.trim() && last.text.length <= audioCaps.max_tts_characters)
          void listen(last.id, ref, true);
        setCart(c.cart);
        setOrders(c.orders);
        setDocuments(c.documents ?? []);
        setAttended(!!c.attended_by_human);
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

  // Mientras un comprobante se lee en segundo plano, se relee la conversación cada pocos segundos.
  // Lo mismo mientras una persona del negocio atiende la conversación (sus respuestas llegan solas).
  // Y mientras un pedido está en camino: los avisos del repartidor llegan solos.
  const reading = documents.some((d) => d.status === "received" || d.status === "processing") || attended
    || orders.some((o) => o.status === "DISPATCHED" || o.status === "IN_TRANSIT");
  useEffect(() => {
    if (!conv || !reading) return;
    const t = window.setInterval(() => reload(conv), 4000);
    return () => window.clearInterval(t);
  }, [conv, reading]);

  async function attach(o: Order, file: File) {
    if (!conv || !source.uploadDocument) return;
    setUploading(o.id);
    setFileNote(null);
    try {
      await source.uploadDocument(conv, o.id, file);
      setFileNote(`Recibimos tu comprobante del pedido #${o.number}. El negocio lo revisa antes de confirmar el pago.`);
      reload(conv);
    } catch (e) {
      setFileNote(e instanceof ApiError ? e.message : "No pude subir el comprobante.");
    } finally {
      setUploading(null);
    }
  }

  async function cancel(o: Order) {
    if (!conv || !source.cancelOrder) return;
    if (!window.confirm(`¿Cancelar el pedido #${o.number}? Se libera lo que te habíamos apartado.`)) return;
    try {
      const updated = await source.cancelOrder(conv, o.id);
      setOrders((list) => list.map((x) => (x.id === o.id ? updated : x)));
      setFileNote(`Cancelaste el pedido #${o.number}.`);
    } catch (e) {
      setFileNote(e instanceof ApiError ? e.message : "No pude cancelar el pedido.");
    }
  }

  async function downloadReceipt(receiptId: string, number?: number) {
    if (!conv || !source.receipt) return;
    try {
      saveBlob(await source.receipt(conv, receiptId), number ? `constancia-pedido-${number}.pdf` : "constancia.pdf");
    } catch {
      setFileNote("No pude descargar la constancia. Probá de nuevo.");
    }
  }

  async function send(text: string, voiceUrl?: string, photoOf?: { url: string; query: string | null }) {
    const msg = text.trim();
    if (!msg || sending) return;
    if (voiceUrl) {
      voiceUrls.current.push(voiceUrl);
      const at = messages.length;
      setMyVoice((v) => ({ ...v, [at]: voiceUrl }));
    }
    if (photoOf) {
      const at = messages.length;
      setMyPhoto((p) => ({ ...p, [at]: photoOf }));
    }
    setPhoto((p) => (p && !p.hint ? p : null)); // la pista de una foto anterior deja de tener sentido
    setPhotoNote(null);
    const g = gen.current;
    reads.current++;
    setInput("");
    setMessages((m) => [...m, { role: "me", text: msg }]);
    setSending(true);
    try {
      const j = await source.chat(msg, conv);
      if (g !== gen.current) return;
      const ref = j.conversation_id === conv?.id ? conv : { id: j.conversation_id, token: j.conversation_token ?? null };
      remember(ref);
      // Con una persona atendiendo, el asistente no responde: no hay burbuja vacía.
      if (j.mode === "human") setAttended(true);
      else setMessages((m) => [...m, { role: "bot", text: j.reply, ui: j.ui }]);
      setCart(j.cart);
      setOrders(j.orders);
      setTrace(j.trace);
      // «Escuchar» necesita el id persistido de la respuesta, que el chat no devuelve.
      if (audioCaps) reload(ref, !!voiceUrl && j.mode !== "human");
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

  // La descripción llega varios renders después: se manda con el `send` vigente (conversación y
  // lista de mensajes actuales), como hace la nota de voz.
  const sendRef = useRef(send);
  sendRef.current = send;

  async function describePhoto(image: Blob) {
    if (!source.photos || (photo && !photo.hint)) return;
    const g = gen.current;
    const url = URL.createObjectURL(image);
    voiceUrls.current.push(url);
    setPhoto({ url });
    setPhotoNote(null);
    const ac = new AbortController();
    photoAbort.current = ac;
    try {
      const r = await source.photos.describe(image, conv, ac.signal);
      if (g !== gen.current) return;
      const text = r.text?.trim();
      if (r.ok && text) {
        setPhoto(null);
        void sendRef.current(text.slice(0, MAX_MESSAGE), undefined, { url, query: r.query });
      } else {
        setPhoto({ url, hint: r.reply || "No llegué a reconocer el producto en la foto. ¿Me contás cuál buscás?" });
        inputRef.current?.focus();
      }
    } catch (e) {
      if (g !== gen.current) return;
      setPhoto(null);
      setPhotoNote(photoError(e));
    } finally {
      if (photoAbort.current === ac) photoAbort.current = null;
    }
  }

  async function listen(id: string, ref: ConversationRef | null = conv, auto = false) {
    if (!ref || !source.audio) return;
    const g = gen.current;
    setVoices((v) => ({ ...v, [id]: { loading: true } }));
    try {
      const blob = await source.audio.speak(ref, id);
      if (g !== gen.current) return;
      const url = URL.createObjectURL(blob);
      voiceUrls.current.push(url);
      setVoices((v) => ({ ...v, [id]: { url, auto } }));
    } catch (e) {
      if (g !== gen.current) return;
      setVoices((v) => ({ ...v, [id]: { error: e instanceof ApiError ? e.message : "No pude generar el audio." } }));
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
                {m.ui?.type === "human" && <span className="msg-author">Equipo de {source.title}</span>}
                {m.ui?.type === "delivery" && (
                  <span className="msg-author delivery-author">
                    <Truck size={13} strokeWidth={1.8} aria-hidden /> Reparto{m.ui.by ? ` · ${m.ui.by}` : ""}
                  </span>
                )}
                {m.role === "me" && myPhoto[i] ? (
                  <div className="bubble me photo-note">
                    <img src={myPhoto[i].url} alt="Tu foto del producto" />
                    <span className="small">Entendí: {myPhoto[i].query || m.text}</span>
                  </div>
                ) : m.role === "me" && myVoice[i] ? (
                  <div className="bubble me voice-note">
                    <audio controls src={myVoice[i]} aria-label="Tu audio" />
                    <span className="small">«{m.text}»</span>
                  </div>
                ) : visibleText(m) && (
                  <div className={`bubble ${m.role === "me" ? "me" : "bot"}${m.ui?.type === "human" || m.ui?.type === "delivery" ? " human" : ""}`}>
                    <Linkified text={m.ui?.payment ? visibleText(m).replace(m.ui.payment.url, "").trim() : visibleText(m)} />
                  </div>
                )}
                {audioCaps && conv && m.role === "bot" && m.id && m.text.trim() && m.text.length <= audioCaps.max_tts_characters && (() => {
                  const v = voices[m.id];
                  return (
                    <div className="listen">
                      {v?.url ? (
                        <audio controls autoPlay={v.auto} src={v.url} aria-label="Respuesta en audio" />
                      ) : (
                        <button className="btn sm ghost" type="button" disabled={v?.loading} onClick={() => void listen(m.id!)}>
                          <Volume2 size={14} aria-hidden="true" /> {v?.loading ? "Preparando audio…" : "Escuchar"}
                        </button>
                      )}
                      {v?.error && <span className="state err small" role="alert">{v.error}</span>}
                    </div>
                  );
                })()}
                {m.ui?.products && m.ui.products.length > 0 && (
                  <Cards cards={m.ui.products} onAction={send} onOpen={setDetail} disabled={sending} />
                )}
                {m.ui?.payment && (
                  <a className="btn primary paybtn" href={m.ui.payment.url} target="_blank" rel="noopener noreferrer">
                    {m.ui.payment.provider === "simulated" ? "Pagar (prueba, no cobra)" : "Pagar con Mercado Pago"}
                  </a>
                )}
                {m.ui?.type === "receipt" && m.ui.receipt_id && source.receipt && (
                  <button className="btn primary paybtn" type="button"
                    onClick={() => void downloadReceipt(m.ui!.receipt_id!, orders.find((o) => o.receipt_id === m.ui!.receipt_id)?.number)}>
                    Descargar constancia (PDF)
                  </button>
                )}
                {m.ui?.type === "receipt" && m.ui.receipt_id && source.rateOrder && conv && (() => {
                  // La encuesta va en el chat, debajo del pago confirmado (también está en «Pedidos»).
                  const o = orders.find((x) => x.receipt_id === m.ui!.receipt_id);
                  return o && RATEABLE.includes(o.status) ? (
                    <RateOrder order={o} onRate={async (score, comment) => {
                      await source.rateOrder!(conv, o.id, score, comment);
                      setOrders((list) => list.map((x) => (x.id === o.id ? { ...x, rating: score } : x)));
                    }} />
                  ) : null;
                })()}
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
            {photo && (
              <div className="msg me">
                <div className="bubble me photo-note">
                  <img src={photo.url} alt="Tu foto del producto" />
                  {!photo.hint && <span className="small" role="status">Mirando la foto…</span>}
                </div>
              </div>
            )}
            {photo?.hint && (
              <div className="msg bot">
                <div className="bubble bot">{photo.hint}</div>
              </div>
            )}
            {sending && <div className="bubble bot typing">Escribiendo…</div>}
            {attended && (
              <div className="human-note" role="status">Te está atendiendo una persona del negocio.</div>
            )}
          </div>

          {audioCaps && source.audio && (
            <VoiceInput
              key={voiceKey}
              caps={audioCaps}
              transcribe={(wav, signal) => source.audio!.transcribe(wav, conv, signal)}
              maxLength={MAX_MESSAGE}
              disabled={sending}
              onVoice={(text, url) => void send(text, url)}
            />
          )}
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              ref={inputRef}
              type="text"
              autoComplete="off"
              placeholder={source.customerView ? "Escribí tu consulta…" : "Escribí como cliente…"}
              maxLength={MAX_MESSAGE}
              aria-label="Mensaje"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            {photoCaps && source.photos && (
              <PhotoInput
                caps={photoCaps}
                disabled={sending || (!!photo && !photo.hint)}
                onPhoto={(image) => void describePhoto(image)}
                onError={setPhotoNote}
              />
            )}
            <button className="btn primary" type="submit" disabled={sending || (!!photo && !photo.hint) || !input.trim()}>
              Enviar
            </button>
          </form>
          {photoNote && <p className="state err small photo-error" role="alert">{photoNote}</p>}
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
                  <div className="order-block" key={o.id}>
                    <div className="row">
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
                    {documents.filter((d) => d.order_number === o.number).map((d) => (
                      <div className="doc-line muted small" key={d.id}>Comprobante: {docLabel(d)}</div>
                    ))}
                    <div className="order-actions">
                      {o.receipt_id && source.receipt && (
                        <button className="btn sm" type="button" onClick={() => void downloadReceipt(o.receipt_id!, o.number)}>
                          Constancia (PDF)
                        </button>
                      )}
                      {source.rateOrder && conv && RATEABLE.includes(o.status) && (
                        <RateOrder order={o} onRate={async (score, comment) => {
                          await source.rateOrder!(conv, o.id, score, comment);
                          setOrders((list) => list.map((x) => (x.id === o.id ? { ...x, rating: score } : x)));
                        }} />
                      )}
                      {source.cancelOrder && o.status === "PENDING_PAYMENT" && (
                        <button className="btn sm ghost" type="button" onClick={() => void cancel(o)}>Cancelar pedido</button>
                      )}
                      {source.uploadDocument && (o.status === "PENDING_PAYMENT" || o.status === "CANCELLED") && (
                        <label className={`btn sm${uploading === o.id ? " disabled" : ""}`}>
                          {uploading === o.id ? "Subiendo…" : "Adjuntar comprobante"}
                          <input
                            type="file"
                            accept="image/jpeg,image/png,application/pdf"
                            hidden
                            disabled={uploading !== null}
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              e.target.value = "";
                              if (f) void attach(o, f);
                            }}
                          />
                        </label>
                      )}
                    </div>
                  </div>
                ))}
                {fileNote && <p className="note" role="status">{fileNote}</p>}
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

/** Encuesta de satisfacción del pedido: 1 a 5 y, si quiere, un comentario. Se puede corregir. */
function RateOrder({ order, onRate }: { order: Order; onRate: (score: number, comment: string) => Promise<void> }) {
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [editing, setEditing] = useState(false);

  if (order.rating && !editing) {
    return (
      <span className="rate-done muted small">
        Calificaste {order.rating}/5. ¡Gracias!{" "}
        <button type="button" className="linkish" onClick={() => { setScore(order.rating ?? null); setEditing(true); }}>Cambiar</button>
      </span>
    );
  }
  async function send() {
    if (score == null) return;
    setState("saving");
    try {
      await onRate(score, comment.trim());
      setState("idle");
      setEditing(false);
    } catch {
      setState("error");
    }
  }
  return (
    <fieldset className="rate">
      <legend className="small">¿Cómo te atendimos en el pedido #{order.number}?</legend>
      <div className="rate-scale" role="radiogroup" aria-label="Calificación de 1 a 5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={score === n}
            className={`chip${score === n ? " on" : ""}`} onClick={() => setScore(n)}>{n}</button>
        ))}
        <span className="muted small">1 = mal · 5 = excelente</span>
      </div>
      {score != null && (
        <div className="rate-send">
          <input type="text" maxLength={500} aria-label="Comentario (opcional)" placeholder="¿Algo para contarnos? (opcional)"
            value={comment} onChange={(e) => setComment(e.target.value)} />
          <button className="btn sm primary" type="button" disabled={state === "saving"} onClick={() => void send()}>Enviar</button>
        </div>
      )}
      {state === "error" && <p className="state err small" role="alert">No pude guardar tu calificación. Probá de nuevo.</p>}
    </fieldset>
  );
}
