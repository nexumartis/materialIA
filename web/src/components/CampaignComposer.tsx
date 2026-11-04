import { useEffect, useMemo, useRef, useState } from "react";
import { Send } from "lucide-react";
import { api, type Audience, type CampaignAudience, type CampaignPreview, type CampaignSummary } from "../lib/api";

/** Variables que el backend completa con datos reales de cada cliente. */
const PLACEHOLDERS: { token: string; hint: string }[] = [
  { token: "{nombre}", hint: "nombre del cliente" },
  { token: "{producto}", hint: "producto" },
  { token: "{monto}", hint: "monto" },
  { token: "{link}", hint: "link para seguir" },
  { token: "{negocio}", hint: "tu negocio" },
];

/** Mensaje de arranque por audiencia: el dueño lo edita, pero no empieza de cero. */
const TEMPLATES: Record<string, string> = {
  abandoned_cart: "Hola {nombre}! Te quedó {producto} en el carrito ({monto}). ¿Te ayudo a terminar la compra? {link}",
  payment_pending: "Hola {nombre}, te escribimos de {negocio}: quedó pendiente el pago de {monto} por {producto}. Podés pagarlo acá: {link}",
  bought: "Hola {nombre}! Gracias por comprar {producto}. Tenemos novedades que te pueden servir: {link}",
  not_bought: "Hola {nombre}! ¿Pudiste ver lo que buscabas? Si querés te ayudo: {link}",
  inactive: "Hola {nombre}! Hace un tiempo que no te vemos por {negocio}. Mirá lo nuevo: {link}",
};
const templateFor = (kind: string) => TEMPLATES[kind] ?? "Hola {nombre}! {link}";

type ParamDef = Audience["params"][number];
const initialParams = (a: Audience): Record<string, string> =>
  Object.fromEntries(a.params.map((p) => [p.name, p.default == null ? "" : String(p.default)]));

/** Del formulario (texto) a lo que espera la API: números para días/montos, null si está vacío. */
function toParams(defs: ParamDef[], raw: Record<string, string>): CampaignAudience["params"] {
  return Object.fromEntries(defs.map((p) => {
    const v = (raw[p.name] ?? "").trim();
    if (!v) return [p.name, null];
    return [p.name, p.type === "text" ? v : Number(v)];
  }));
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
/** "2026-11-05T10:30" para el mínimo del datetime-local (hora local, sin segundos). */
const localNow = () => {
  const d = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
  return d.toISOString().slice(0, 16);
};

/** Nueva campaña: a quién, qué le decimos (con vista previa real) y cuándo. */
export function CampaignComposer({ audiences, onClose, onLaunched }: {
  audiences: Audience[];
  onClose: () => void;
  onLaunched: (c: CampaignSummary) => void;
}) {
  const [kind, setKind] = useState(audiences[0]?.kind ?? "");
  const audience = audiences.find((a) => a.kind === kind) ?? audiences[0];
  const [raw, setRaw] = useState<Record<string, string>>(() => (audience ? initialParams(audience) : {}));
  const [name, setName] = useState(audience?.label ?? "");
  const [nameEdited, setNameEdited] = useState(false);
  const [message, setMessage] = useState(templateFor(kind));
  const [messageEdited, setMessageEdited] = useState(false);
  const [when, setWhen] = useState<"now" | "later">("now");
  const [at, setAt] = useState("");
  const [preview, setPreview] = useState<CampaignPreview | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Si se creó el borrador pero falló el lanzamiento, el reintento lanza ése (no duplica la campaña).
  const [draftId, setDraftId] = useState<string | null>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const params = useMemo(() => (audience ? toParams(audience.params, raw) : {}), [audience, raw]);
  const key = JSON.stringify({ kind, params, message });

  function pickAudience(a: Audience) {
    setKind(a.kind);
    setRaw(initialParams(a));
    if (!nameEdited) setName(a.label);
    if (!messageEdited) setMessage(templateFor(a.kind));
    setDraftId(null);
  }

  // Vista previa en vivo (con pausa de ~500 ms para no consultar en cada tecla). Una respuesta
  // vieja nunca pisa a una nueva: sólo se guarda si la clave sigue siendo la vigente.
  useEffect(() => {
    if (!audience || !message.trim()) return;
    let alive = true;
    setPreviewError(null);
    const t = window.setTimeout(() => {
      api.previewCampaign({ kind, params }, message).then(
        (p) => { if (alive) { setPreview(p); setPreviewKey(key); } },
        (e) => { if (alive) setPreviewError(e instanceof Error ? e.message : "No pude calcular a quién le llega."); },
      );
    }, 500);
    return () => { alive = false; window.clearTimeout(t); };
  }, [key]); // `key` resume kind, params y message.

  function insert(token: string) {
    const el = textRef.current;
    const start = el?.selectionStart ?? message.length;
    const end = el?.selectionEnd ?? message.length;
    setMessage(message.slice(0, start) + token + message.slice(end));
    setMessageEdited(true);
    // Devolver el foco al texto con el cursor después de lo insertado.
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      el.setSelectionRange(start + token.length, start + token.length);
    });
  }

  const fresh = preview != null && previewKey === key;
  const count = fresh ? preview.count : 0;
  const atIso = when === "later" && at ? new Date(at).toISOString() : null;
  const laterInvalid = when === "later" && (!at || new Date(at).getTime() <= Date.now());
  const canLaunch = Boolean(audience) && fresh && count > 0 && name.trim() !== "" && message.trim() !== "" && !laterInvalid && !busy;

  async function launch() {
    if (!audience || !canLaunch) return;
    const whenText = atIso ? `el ${new Date(atIso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" })}` : "ahora";
    if (!window.confirm(`Se va a enviar a ${plural(count, "cliente", "clientes")} (${whenText}). ¿Seguimos?`)) return;
    setBusy(true);
    setError(null);
    try {
      let id = draftId;
      if (!id) {
        const draft = await api.createCampaign({ name: name.trim(), audience: { kind, params }, message, scheduled_at: atIso });
        id = draft.id;
        setDraftId(id);
      }
      onLaunched(await api.launchCampaign(id, atIso));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo lanzar la campaña.");
    } finally {
      setBusy(false);
    }
  }

  if (!audience) {
    return <p className="state err" role="alert">No hay audiencias disponibles para armar una campaña.</p>;
  }

  return (
    <section className="results-card camp-new" aria-labelledby="camp-new-title">
      <div className="camp-new-head">
        <h2 id="camp-new-title">Nueva campaña</h2>
        <button className="btn sm ghost" type="button" onClick={onClose}>Cancelar</button>
      </div>

      <fieldset className="camp-step">
        <legend><span className="camp-n" aria-hidden>1</span> ¿A quién le escribimos?</legend>
        <div className="camp-options">
          {audiences.map((a) => (
            <label key={a.kind} className={`camp-option${a.kind === kind ? " on" : ""}`}>
              <input type="radio" name="camp-audience" value={a.kind} checked={a.kind === kind}
                onChange={() => pickAudience(a)} />
              <span><b>{a.label}</b><span className="muted small">{a.description}</span></span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="camp-step">
        <legend><span className="camp-n" aria-hidden>2</span> Detalles</legend>
        <div className="camp-params">
          <label className="field camp-name">
            <span>Nombre de la campaña</span>
            <input value={name} maxLength={120} required
              onChange={(e) => { setName(e.target.value); setNameEdited(true); }} />
            <small>Sólo lo ves vos.</small>
          </label>
          {audience.params.map((p) => (
            <label key={p.name} className="field">
              <span>{p.label}</span>
              <span className="camp-affix">
                {p.type === "amount" && <span aria-hidden>$</span>}
                <input type={p.type === "text" ? "text" : "number"} inputMode={p.type === "text" ? undefined : "numeric"}
                  min={p.type === "text" ? undefined : p.type === "days" ? 1 : 0}
                  value={raw[p.name] ?? ""} placeholder={p.type === "text" ? "Opcional" : undefined}
                  onChange={(e) => { setRaw((r) => ({ ...r, [p.name]: e.target.value })); setDraftId(null); }} />
                {p.type === "days" && <span aria-hidden>días</span>}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="camp-step">
        <legend><span className="camp-n" aria-hidden>3</span> El mensaje</legend>
        <div className="camp-compose">
          <div>
            <label className="field">
              <span>Texto</span>
              <textarea ref={textRef} rows={5} value={message}
                onChange={(e) => { setMessage(e.target.value); setMessageEdited(true); setDraftId(null); }} />
            </label>
            <div className="suggest" role="group" aria-label="Insertar dato del cliente">
              <span className="suggest-label">Insertar:</span>
              {PLACEHOLDERS.map((p) => (
                <button key={p.token} type="button" className="chip camp-token" title={p.hint}
                  aria-label={`Insertar ${p.hint}`} onClick={() => insert(p.token)}>{p.token}</button>
              ))}
            </div>
            <p className="muted small">Cada cliente recibe sus propios datos: nombre, producto y monto reales.</p>
          </div>
          <Preview preview={fresh ? preview : null} loading={!fresh && !previewError && message.trim() !== ""}
            error={previewError} emptyMessage={!message.trim()} />
        </div>
      </fieldset>

      <fieldset className="camp-step">
        <legend><span className="camp-n" aria-hidden>4</span> ¿Cuándo?</legend>
        <div className="camp-when">
          <label className="small"><input type="radio" name="camp-when" checked={when === "now"} onChange={() => setWhen("now")} /> Enviar ahora</label>
          <label className="small"><input type="radio" name="camp-when" checked={when === "later"} onChange={() => setWhen("later")} /> Programar</label>
          {when === "later" && (
            <label className="field">
              <span>Fecha y hora</span>
              <input type="datetime-local" value={at} min={localNow()} onChange={(e) => setAt(e.target.value)} />
            </label>
          )}
        </div>
        {error && <p className="state err" role="alert">{error}</p>}
        <div className="camp-actions">
          <button className="btn primary" type="button" disabled={!canLaunch} onClick={() => void launch()}>
            <Send size={15} strokeWidth={1.8} aria-hidden />
            {busy ? "Lanzando…" : when === "now" ? "Enviar ahora" : "Programar"}
          </button>
          <span className="muted small" aria-live="polite">
            {fresh && count === 0 ? "Nadie entra en esta audiencia todavía: probá con otros valores."
              : laterInvalid && when === "later" ? "Elegí una fecha y hora futura." : ""}
          </span>
        </div>
      </fieldset>
    </section>
  );
}

/** A cuántos les llega y cómo se ve el mensaje ya completado para algunos clientes. */
function Preview({ preview, loading, error, emptyMessage }: {
  preview: CampaignPreview | null; loading: boolean; error: string | null; emptyMessage: boolean;
}) {
  return (
    <div className="camp-preview" aria-live="polite" aria-busy={loading}>
      {error ? <p className="state err" role="alert">{error}</p>
        : emptyMessage ? <p className="muted small">Escribí el mensaje para ver a quién le llega.</p>
        : !preview ? <p className="muted small">Calculando a quién le llega…</p>
        : (
          <>
            <p className="camp-count"><b>Le llega a {plural(preview.count, "cliente", "clientes")}</b></p>
            {(preview.excluded.opted_out > 0 || preview.excluded.recently_contacted > 0) && (
              <p className="muted small">
                No le llega a: {[
                  preview.excluded.opted_out > 0 && `${preview.excluded.opted_out} que se ${preview.excluded.opted_out === 1 ? "dio" : "dieron"} de baja`,
                  preview.excluded.recently_contacted > 0 && `${preview.excluded.recently_contacted} que ya ${preview.excluded.recently_contacted === 1 ? "recibió" : "recibieron"} una campaña esta semana`,
                ].filter(Boolean).join(" · ")}.
              </p>
            )}
            {preview.sample.length > 0 && (
              <ul className="camp-sample" aria-label="Ejemplos del mensaje">
                {preview.sample.slice(0, 5).map((s, i) => (
                  <li key={`${s.name}-${i}`}>
                    <span className="small"><b>{s.name}</b>{s.detail && <span className="muted"> · {s.detail}</span>}</span>
                    <div className="bubble bot">{s.message}</div>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
    </div>
  );
}
