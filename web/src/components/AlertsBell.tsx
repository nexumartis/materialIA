import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Bell, CalendarDays, MessagesSquare, Receipt, ShoppingBag, ThumbsDown, type LucideIcon } from "lucide-react";
import { api, type Alert } from "../lib/api";

const ICON: Record<Alert["kind"], LucideIcon> = {
  handoff: MessagesSquare, order: ShoppingBag, receipt: Receipt, appointment: CalendarDays, rating: ThumbsDown };
const EVERY_MS = 30_000;
const STORE = "pv.avisos.vistos";

function loadSeen(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(STORE) || "[]") as string[]); } catch { return new Set(); }
}
function saveSeen(keys: Set<string>) {
  try { localStorage.setItem(STORE, JSON.stringify([...keys].slice(-300))); } catch { /* sin almacenamiento: no pasa nada */ }
}
const ago = (iso: string) => {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  return m < 1 ? "recién" : m < 60 ? `hace ${m} min` : m < 1440 ? `hace ${Math.round(m / 60)} h` : `hace ${Math.round(m / 1440)} d`;
};

/** Centro de avisos: campanita con lo nuevo; al abrirla, lo visible queda como visto. */
export function AlertsBell({ enabled }: { enabled: boolean }) {
  const [items, setItems] = useState<Alert[]>([]);
  const [seen, setSeen] = useState<Set<string>>(loadSeen);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; bottom: number } | null>(null);

  const load = useCallback(() => { api.alerts().then(setItems, () => {}); }, []);
  useEffect(() => {
    if (!enabled) return;
    load();
    const t = window.setInterval(load, EVERY_MS);
    return () => window.clearInterval(t);
  }, [enabled, load]);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !box.current?.contains(e.target as Node) && !pop.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [open]);

  if (!enabled) return null;
  const unseen = items.filter((a) => !seen.has(a.key)).length;
  function toggle() {
    if (!open) {
      // El panel va en <body> (fuera de la barra lateral) para quedar sobre cualquier pantalla.
      const r = box.current?.getBoundingClientRect();
      if (r) setPos({ left: r.right + 8, bottom: Math.max(8, window.innerHeight - r.bottom) });
      const next = new Set([...seen, ...items.map((a) => a.key)]);
      setSeen(next);
      saveSeen(next);
    }
    setOpen((v) => !v);
  }
  return (
    <div className="alerts" ref={box}>
      <button type="button" className="nav-action alerts-btn" aria-expanded={open} aria-haspopup="true" onClick={toggle}>
        <Bell size={16} strokeWidth={1.8} aria-hidden /> Avisos
        {unseen > 0 && <span className="nav-count" aria-label={`${unseen} nuevos`}>{unseen}</span>}
      </button>
      {open && createPortal(
        <div className="alerts-pop" role="dialog" aria-label="Avisos" ref={pop}
          style={pos && window.innerWidth > 900 ? { left: pos.left, bottom: pos.bottom } : undefined}>
          <div className="alerts-head">Avisos</div>
          {items.length === 0 ? <p className="muted small">No hay nada pendiente. 🎉</p> : (
            <ul>
              {items.map((a) => {
                const Icon = ICON[a.kind];
                return (
                  <li key={a.key}>
                    <a href={a.href} onClick={() => setOpen(false)}>
                      <Icon size={15} strokeWidth={1.8} aria-hidden />
                      <span>{a.text}<small className="muted"> · {ago(a.at)}</small></span>
                    </a>
                  </li>
                );
              })}
            </ul>
          )}
        </div>,
        document.body,
      )}
    </div>
  );
}
