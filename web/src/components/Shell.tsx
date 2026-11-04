import { useEffect, useState, type ReactNode } from "react";
import {
  AppWindow, BarChart3, Bot, CalendarDays, Code2, LayoutDashboard, Settings, PlugZap, LogIn, LogOut, Megaphone, Menu, MessageCircle, MessagesSquare, Package, Route, ShoppingBag, SlidersHorizontal, Target, Truck, Users,
  type LucideIcon,
} from "lucide-react";
import type { Health } from "../lib/api";
import { usePendingHandoffs } from "../lib/alerts";
import { useSession } from "../lib/session";
import { AlertsBell } from "./AlertsBell";

export type Section = "oportunidades" | "conversaciones" | "pedidos" | "asistente" | "catalogo" | "agente" | "venta" | "equipo" | "resultados" | "integraciones" | "turnos" | "campanias" | "web" | "entregas" | "ruta" | "inicio" | "login" | "signup";

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
  equipo: "Equipo",
  resultados: "Resultados",
  integraciones: "Integraciones",
  turnos: "Turnos",
  campanias: "Campañas",
  web: "Chat en tu web",
  entregas: "Entregas",
  ruta: "Mi hoja de ruta",
  inicio: "Inicio",
  login: "Iniciar sesión",
  signup: "Registrá tu negocio",
};

/** Navegación agrupada como en un SaaS: Ventas, Tu agente y Herramientas. */
interface NavItem { section: Section | null; href: string; label: string; icon: LucideIcon; also?: Section[]; external?: boolean; ownerOnly?: boolean }
const NAV: { title: string; items: NavItem[] }[] = [
  { title: "Ventas", items: [
    { section: "inicio", href: "#/inicio", label: "Inicio", icon: LayoutDashboard, ownerOnly: true },
    { section: "resultados", href: "#/resultados", label: "Resultados", icon: BarChart3, ownerOnly: true },
    { section: "conversaciones", href: "#/conversaciones", label: "Conversaciones", icon: MessagesSquare },
    { section: "oportunidades", href: "#/oportunidades", label: "Oportunidades", icon: Target },
    { section: "pedidos", href: "#/pedidos", label: "Pedidos", icon: ShoppingBag },
    { section: "entregas", href: "#/entregas", label: "Entregas", icon: Truck },
    { section: "campanias", href: "#/campanias", label: "Campañas", icon: Megaphone, ownerOnly: true },
    { section: "turnos", href: "#/turnos", label: "Turnos", icon: CalendarDays },
  ] },
  { title: "Tu agente", items: [
    // «Mi agente» abre el asistente paso a paso; el formulario completo queda como ajustes.
    { section: "asistente", href: "#/asistente", label: "Mi agente", icon: Bot, ownerOnly: true },
    { section: "agente", href: "#/agente", label: "Ajustes del agente", icon: SlidersHorizontal, ownerOnly: true },
    { section: "catalogo", href: "#/catalogo", label: "Catálogo", icon: Package },
  ] },
  { title: "Herramientas", items: [
    { section: "web", href: "#/web", label: "Chat en tu web", icon: AppWindow, ownerOnly: true },
    { section: "venta", href: "#/venta", label: "Demo del agente", icon: MessageCircle },
    { section: "ruta", href: "#/ruta", label: "Mi hoja de ruta", icon: Route },
    { section: "equipo", href: "#/equipo", label: "Equipo", icon: Users, ownerOnly: true },
    { section: "integraciones", href: "#/integraciones", label: "Integraciones", icon: PlugZap, ownerOnly: true },
  ] },
];
// El reparto no entra al panel: sólo ve su hoja de ruta.
const DRIVER_NAV: { title: string; items: NavItem[] }[] = [
  { title: "Reparto", items: [{ section: "ruta", href: "#/ruta", label: "Mi hoja de ruta", icon: Route }] },
];
const ROLE_LABEL = { owner: "Dueño", staff: "Equipo", driver: "Reparto" } as const;

export function Shell({ health, active, children }: Props) {
  const [open, setOpen] = useState(false);
  const { status, me, signOut } = useSession();
  const driver = me?.role === "driver";
  const pending = usePendingHandoffs(status === "ready" && !driver);
  const nav = driver ? DRIVER_NAV : NAV;
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
          {status === "ready" && me && (
            <div className="store-card" title={me.business_name}>
              <span className="store-avatar" aria-hidden>{me.business_name.trim().charAt(0).toUpperCase()}</span>
              <span className="store-name">{me.business_name}</span>
            </div>
          )}

          <nav className="nav" aria-label="Secciones">
            {nav.map((group) => (
              <div className="nav-group" key={group.title}>
                <span className="nav-title" aria-hidden>{group.title}</span>
                {group.items.filter((i) => !i.ownerOnly || me?.role === "owner" || !me).map(({ section, href, label, icon: Icon }) => {
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

          <AlertsBell enabled={status === "ready" && Boolean(me) && !driver} />
          <div className="sidebar-foot">
            {!driver && <div className="foot-status">
              <span className={`modepill ${live ? "live" : "demo"}`}>
                <span className="dot" aria-hidden />
                {live ? "IA activa" : "Modo demo (sin IA)"}
              </span>
              {health?.llm.model && <span className="foot-note" title={health.llm.model}>{health.llm.model}</span>}
              {active === "venta" && <span className="foot-note">Datos sintéticos de demostración.</span>}
            </div>}
            {status === "ready" && me ? (
              <div className="user-card">
                <div className="user-row">
                  <span className="store-avatar" aria-hidden>{me.business_name.trim().charAt(0).toUpperCase()}</span>
                  <span><b>{ROLE_LABEL[me.role] ?? "Equipo"}</b><small className="muted">{me.business_name}</small></span>
                </div>
                {me.role === "owner" && (
                  <a className="nav-action" href="#/agente" onClick={() => setOpen(false)}>
                    <Settings size={16} strokeWidth={1.8} aria-hidden /> Configuración
                  </a>
                )}
                <button className="nav-action" type="button" onClick={() => void signOut()}>
                  <LogOut size={16} strokeWidth={1.8} aria-hidden /> Cerrar sesión
                </button>
              </div>
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
