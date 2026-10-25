import { useEffect, useRef, useState } from "react";
import { api, type ChatResponse, type Company, type Health, type Requirements } from "../lib/api";

interface Msg {
  role: "me" | "bot";
  text: string;
}

const GREETING =
  "¡Hola! Soy el asistente virtual del negocio (demo). Contame qué cerramiento necesitás.";

const SUGGESTIONS = [
  "Quiero una mampara corrediza negra de 1,60 × 1,90 en Tigre",
  "Necesito un cerramiento de baño blanco de 1,20 × 1,95",
  "¿Hacen ventanas corredizas a medida?",
];

const REQ_LABELS: Record<string, string> = {
  category: "Rubro",
  tipo: "Tipo",
  color: "Color",
  material: "Material",
  ancho_mm: "Ancho",
  alto_mm: "Alto",
  localidad: "Localidad",
  customer_name: "Cliente",
  customer_phone: "Teléfono",
  customer_email: "Email",
  quantity: "Cantidad",
  product_id: "Producto",
};

function reqValue(k: string, v: unknown): string {
  if ((k === "ancho_mm" || k === "alto_mm") && v != null && v !== "") return `${v} mm`;
  return String(v);
}

export function Chat({ company, health }: { company: Company; health: Health | null }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [convId, setConvId] = useState<string | null>(null);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  // Al cambiar de empresa, se reinicia la conversación.
  useEffect(() => {
    setMessages([]);
    setConvId(null);
    setResult(null);
    setInput("");
  }, [company]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || sending) return;
    setInput("");
    setMessages((m) => [...m, { role: "me", text: msg }]);
    setSending(true);
    try {
      const j = await api.chat(company, msg, convId);
      setConvId(j.conversation_id);
      setMessages((m) => [...m, { role: "bot", text: j.reply }]);
      setResult(j);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "bot", text: "No pude conectar con la API local. ¿Está corriendo el backend en el puerto 8077?" },
      ]);
    } finally {
      setSending(false);
    }
  }

  const live = health?.llm.mode === "live";

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Chat demo</h1>
          <p className="finding">
            Asistente del negocio sobre datos sintéticos. Nunca afirma precios inventados.
          </p>
        </div>
        <div className="right">
          <span className="statusline">
            <span className={`sdot ${health ? (health.db.reachable ? "ok" : "off") : "off"}`} />
            {health
              ? `API ${health.status} · db ${health.db.reachable ? "ok" : "off"} · ${live ? "live" : "mock"}`
              : "API no disponible"}
          </span>
        </div>
      </div>

      <div className="chat-grid">
        <section className="chatcol" aria-label="Conversación">
          <div className="chatlog" ref={logRef}>
            <div className="bubble bot">{GREETING}</div>
            {messages.length === 0 && (
              <div className="suggest">
                <span className="suggest-label">Probá con:</span>
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`bubble ${m.role === "me" ? "me" : "bot"}`}>
                {m.text}
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
              placeholder="Escribí tu consulta…"
              aria-label="Mensaje"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="btn primary" type="submit" disabled={sending || !input.trim()}>
              Enviar
            </button>
          </form>
          <p className="note">
            La respuesta sale de la API local <code>/sandbox/chat</code>. No hay WhatsApp ni LLM real
            salvo que configures una API key.
          </p>
        </section>

        <aside className="rail" aria-label="Ficha capturada">
          <div>
            <h2 className="panel-title">Ficha del pedido</h2>
            <p className="panel-sub">Requisitos que el asistente fue capturando.</p>
            <Ficha result={result} />
          </div>
          <div>
            <h2 className="panel-title">Última oportunidad</h2>
            <p className="panel-sub">Se registra cuando hay datos suficientes.</p>
            {result?.opportunity_id ? (
              <div className="well">id: {result.opportunity_id}</div>
            ) : (
              <div className="empty-box">Sin oportunidad registrada.</div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function Ficha({ result }: { result: ChatResponse | null }) {
  const req: Requirements = result?.collected_requirements || {};
  const keys = Object.keys(req);
  if (!keys.length) {
    return <div className="empty-box">Sin requisitos capturados aún.</div>;
  }
  return (
    <>
      <div className="kv">
        {keys.map((k) => (
          <div className="row" key={k}>
            <span className="k">{REQ_LABELS[k] || k}</span>
            <span className="v">{reqValue(k, req[k])}</span>
          </div>
        ))}
      </div>
      {result && (
        <div className="flags">
          {result.missing_fields.length > 0 && (
            <span className="pill warn">faltan: {result.missing_fields.join(", ")}</span>
          )}
          <span className={`pill ${result.requires_human ? "neg" : "pos"}`}>
            {result.requires_human ? "requiere revisión humana" : "sin revisión pendiente"}
          </span>
          <span className="pill neu">modo: {result.mode}</span>
        </div>
      )}
    </>
  );
}
