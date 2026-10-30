import { useEffect, useState, type ReactNode } from "react";
import {
  Bot, Code2, LogIn, LogOut, Menu, MessageCircle, MessagesSquare, Package, ShoppingBag, SlidersHorizontal, Target,
  type LucideIcon,
} from "lucide-react";
import type { Health } from "../lib/api";
import { usePendingHandoffs } from "../lib/alerts";
import { useSession } from "../lib/session";
import { Mark } from "./Mark";

export type Section = "oportunidades" | "conversaciones" | "pedidos" | "asistente" | "catalogo" | "agente" | "venta" | "login" | "signup";

interface Props {
  health: Health | null;
  active: Section;
  children: ReactNode;
}

const TITLES: Record<Section, string> = {
  oportunidades: "Oportunidades",
  conversaciones: "Conversaciones",
  pedidos: "Pedidos",
  catalogo: "Catálogo",
  agente: "Ajustes del agente",
  asistente: "Mi agente",
  venta: "Demo del agente",
  login: "Iniciar sesión",
  signup: "Registrá tu negocio",
};

/** Navegación agrupada como en un SaaS: Ventas, Tu agente y Herramientas. */
interface NavItem { section: Section | null; href: string; label: string; icon: LucideIcon; also?: Section[]; external?: boolean }
const NAV: { title: string; items: NavItem[] }[] = [
  { title: "Ventas", items: [
    { section: "conversaciones", href: "#/conversaciones", label: "Conversaciones", icon: MessagesSquare },
    { section: "oportunidades", href: "#/oportunidades", label: "Oportunidades", icon: Target },
    { section: "pedidos", href: "#/pedidos", label: "Pedidos", icon: ShoppingBag },
  ] },
  { title: "Tu agente", items: [
    // «Mi agente» abre el asistente paso a paso; el formulario completo queda como ajustes.
    { section: "asistente", href: "#/asistente", label: "Mi agente", icon: Bot },
    { section: "agente", href: "#/agente", label: "Ajustes del agente", icon: SlidersHorizontal },
    { section: "catalogo", href: "#/catalogo", label: "Catálogo", icon: Package },
  ] },
  { title: "Herramientas", items: [
    { section: "venta", href: "#/venta", label: "Demo del agente", icon: MessageCircle },
  ] },
];

export function Shell({ health, active, children }: Props) {
  const [open, setOpen] = useState(false);
  const { status, me, signOut } = useSession();
  const pending = usePendingHandoffs(status === "ready");
  const live = health?.llm.mode === "live";
  const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8077";

  // Cerrar el menú móvil con Escape.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    document.body.classList.toggle("nav-open", open);
    return () => document.body.classList.remove("nav-open");
  }, [open]);

  return (
    <>
      <div className="topbar">
        <button
          className="menu"
          type="button"
          aria-label="Abrir menú"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <Menu size={20} strokeWidth={1.8} aria-hidden />
        </button>
        <b>{TITLES[active]}</b>
      </div>

      <div className="scrim" onClick={() => setOpen(false)} />

      <div className="app">
        <aside className="sidebar">
          <div className="brand">
            <Mark />
            <div>
              <b title={me?.business_name}>{status === "ready" && me ? me.business_name : "Presupuesto Vivo"}</b>
              <span>{status === "ready" && me ? "Presupuesto Vivo" : "Agente de ventas"}</span>
            </div>
          </div>

          <nav className="nav" aria-label="Secciones">
            {NAV.map((group) => (
              <div className="nav-group" key={group.title}>
                <span className="nav-title" aria-hidden>{group.title}</span>
                {group.items.map(({ section, href, label, icon: Icon }) => {
                  const current = section === active;
                  return (
                    <a key={href} className={current ? "active" : ""} href={href}
                      aria-current={current ? "page" : undefined} onClick={() => setOpen(false)}>
                      <Icon size={16} strokeWidth={1.8} aria-hidden /> {label}
                      {section === "conversaciones" && pending > 0 && (
                        <span className="nav-count" aria-label={`${pending} sin atender`}>{pending}</span>
                      )}
                    </a>
                  );
                })}
                {group.title === "Herramientas" && (
                  <a href={`${apiBase}/docs`} target="_blank" rel="noopener noreferrer">
                    <Code2 size={16} strokeWidth={1.8} aria-hidden /> API · Swagger
                  </a>
                )}
              </div>
            ))}
          </nav>

          <div className="sidebar-foot">
            <div className="foot-status">
              <span className={`modepill ${live ? "live" : "demo"}`}>
                <span className="dot" aria-hidden />
                {live ? "IA activa" : "Modo demo (sin IA)"}
              </span>
              {health?.llm.model && <span className="foot-note" title={health.llm.model}>{health.llm.model}</span>}
              {active === "venta" && <span className="foot-note">Datos sintéticos de demostración.</span>}
            </div>
            {status === "ready" && me ? (
              <button className="nav-action" type="button" onClick={() => void signOut()}>
                <LogOut size={16} strokeWidth={1.8} aria-hidden /> Cerrar sesión
              </button>
            ) : status !== "unconfigured" ? (
              <a className="nav-action" href="#/login" onClick={() => setOpen(false)}>
                <LogIn size={16} strokeWidth={1.8} aria-hidden /> Iniciar sesión
              </a>
            ) : null}
          </div>
        </aside>

        <main className="main">{children}</main>
      </div>
    </>
  );
}
