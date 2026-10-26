import { useEffect, useState, type ReactNode } from "react";
import type { Health } from "../lib/api";
import { useSession } from "../lib/session";
import { Mark } from "./Mark";

export type Section = "oportunidades" | "pedidos" | "catalogo" | "agente" | "venta" | "login" | "signup";

interface Props {
  health: Health | null;
  active: Section;
  children: ReactNode;
}

const TITLES: Record<Section, string> = {
  oportunidades: "Oportunidades",
  pedidos: "Pedidos",
  catalogo: "Catálogo",
  agente: "Mi agente",
  venta: "Demo del agente",
  login: "Iniciar sesión",
  signup: "Registrá tu negocio",
};

function IconList() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function IconChat() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M4 5h16v10H9l-5 4V5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}
function IconDoc() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M6 3h8l4 4v14H6z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M14 3v4h4" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function Shell({ health, active, children }: Props) {
  const [open, setOpen] = useState(false);
  const { status, me, signOut } = useSession();
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
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>
        <b>{TITLES[active]}</b>
      </div>

      <div className="scrim" onClick={() => setOpen(false)} />

      <div className="app">
        <aside className="sidebar">
          <div className="brand">
            <Mark />
            <div>
              <b>Presupuesto Vivo</b>
              <span>Agente de ventas</span>
            </div>
          </div>


          <nav className="nav" aria-label="Secciones">
            <a
              className={active === "oportunidades" ? "active" : ""}
              href="#/oportunidades"
              aria-current={active === "oportunidades" ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <IconList /> Oportunidades
            </a>
            <a
              className={active === "pedidos" ? "active" : ""}
              href="#/pedidos"
              aria-current={active === "pedidos" ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <IconList /> Pedidos
            </a>
            <a
              className={active === "catalogo" ? "active" : ""}
              href="#/catalogo"
              aria-current={active === "catalogo" ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <IconDoc /> Catálogo
            </a>
            <a
              className={active === "agente" ? "active" : ""}
              href="#/agente"
              aria-current={active === "agente" ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <IconChat /> Mi agente
            </a>
            <a
              className={active === "venta" ? "active" : ""}
              href="#/venta"
              aria-current={active === "venta" ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <IconChat /> Demo del agente
            </a>
            <a href={`${apiBase}/docs`} target="_blank" rel="noopener noreferrer">
              <IconDoc /> API · Swagger
            </a>
          </nav>

          <div className="sidebar-foot">
            <div className="account">
              {status === "ready" && me ? (
                <>
                  <span className="who">Tu negocio</span>
                  <b title={me.business_name}>{me.business_name}</b>
                  <button className="btn ghost sm" type="button" onClick={() => void signOut()}>
                    Cerrar sesión
                  </button>
                </>
              ) : status !== "unconfigured" ? (
                <a className="btn sm" href="#/login" onClick={() => setOpen(false)}>
                  Iniciar sesión
                </a>
              ) : null}
            </div>
            <span className={`modepill ${live ? "live" : "demo"}`}>
              <span className="dot" />
              {live ? "Modo live" : "Modo demo"}
            </span>
            {health?.llm.model && <span className="foot-note">{health.llm.model}</span>}
            {active === "venta" && <span className="foot-note">Datos sintéticos de demostración.</span>}
          </div>
        </aside>

        <main className="main">{children}</main>
      </div>
    </>
  );
}
