import { useEffect, useState } from "react";
import { RotateCcw, X } from "lucide-react";
import type { WidgetConfig } from "../lib/api";

/** "ferreteria-centro" → "Ferreteria Centro": alcanza para el encabezado de la vista previa. */
const storeName = (slug: string) =>
  slug.split("-").filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(" ") || "Tu tienda";

/** Vista previa del chat en una web de mentira: mismo botón, globito y panel que el widget real
 *  (ver public/widget.js). No carga la tienda: es sólo para ver cómo queda. */
export function WidgetPreview({ config, slug, host }: { config: WidgetConfig; slug: string; host: string | null }) {
  const [open, setOpen] = useState(false);
  const [bubble, setBubble] = useState(false);
  const [left, setLeft] = useState(0); // segundos que faltan para el saludo
  const [run, setRun] = useState(0); // «Ver de nuevo» reinicia la cuenta
  const greeting = config.greeting.trim();
  const delay = config.greeting_delay_s;

  // El saludo aparece a los N segundos, igual que en la web. Escribir el texto no reinicia la
  // cuenta (sería molesto verlo desaparecer en cada tecla); cambiar la demora o «Ver de nuevo», sí.
  useEffect(() => {
    setBubble(false);
    setOpen(false);
    setLeft(delay);
    if (delay <= 0) { setBubble(true); return; }
    const started = Date.now();
    const t = window.setInterval(() => {
      const rest = Math.max(0, delay - Math.floor((Date.now() - started) / 1000));
      setLeft(rest);
      if (rest === 0) { setBubble(true); window.clearInterval(t); }
    }, 250);
    return () => window.clearInterval(t);
  }, [delay, run]);

  const side = config.position === "left" ? "left" : "right";
  const showBubble = bubble && !open && greeting !== "";
  const waiting = !bubble && greeting !== "" && !open;

  return (
    <div className="wc-preview">
      <div className={`wc-site wc-${side}`} aria-label="Vista previa en una página de ejemplo" role="group">
        <div className="wc-chrome" aria-hidden>
          <span className="wc-dots"><i /><i /><i /></span>
          <span className="wc-url">{host || "tu-sitio.com"}</span>
        </div>
        <div className="wc-page" aria-hidden>
          <div className="wc-sk wc-sk-nav" />
          <div className="wc-sk wc-sk-hero" />
          <div className="wc-sk-row"><div className="wc-sk" /><div className="wc-sk" /><div className="wc-sk" /></div>
          <div className="wc-sk wc-sk-line" />
          <div className="wc-sk wc-sk-line short" />
        </div>

        {open && (
          <div className="wc-panel" role="dialog" aria-label={`Chat de ${storeName(slug)} (vista previa)`}>
            <div className="wc-panel-head">{storeName(slug)}</div>
            <div className="wc-panel-body">
              <div className="wc-msg">{greeting || "¡Hola! ¿En qué te ayudo?"}</div>
            </div>
            <div className="wc-panel-input" aria-hidden>Escribí tu mensaje…</div>
          </div>
        )}

        {showBubble && (
          <div className="wc-bubble" role="status">
            <button type="button" className="wc-bubble-x" aria-label="Cerrar saludo" onClick={() => setBubble(false)}>
              <X size={13} strokeWidth={2} aria-hidden />
            </button>
            {greeting}
          </div>
        )}

        <button type="button" className="wc-btn" style={{ background: config.color }} aria-expanded={open}
          onClick={() => setOpen((v) => !v)}>
          {open ? "Cerrar" : config.label.trim() || "¿Te ayudo?"}
        </button>
      </div>

      <div className="wc-preview-foot">
        <span className="muted small" aria-live="polite">
          {greeting === "" ? "Sin saludo automático." : waiting ? `El saludo aparece en ${left} s…` : "Tocá el botón para ver el chat."}
        </span>
        <button type="button" className="btn sm ghost" onClick={() => setRun((n) => n + 1)}>
          <RotateCcw size={14} strokeWidth={1.8} aria-hidden /> Ver de nuevo
        </button>
      </div>
    </div>
  );
}
