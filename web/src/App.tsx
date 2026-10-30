import { useEffect, useState } from "react";
import { api, type Health } from "./lib/api";
import { useSession } from "./lib/session";
import { Mark } from "./components/Mark";
import { Shell, type Section } from "./components/Shell";
import { Opportunities } from "./pages/Opportunities";
import { Sales } from "./pages/Sales";
import { Store } from "./pages/Store";
import { AgentSetup } from "./pages/AgentSetup";
import { AgentWizard } from "./pages/AgentWizard";
import { Catalog } from "./pages/Catalog";
import { OrdersPage } from "./pages/OrdersPage";
import { Inbox } from "./pages/Inbox";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const on = () => setHash(window.location.hash);
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
}

function sectionFor(hash: string): Section {
  // "#/chat" era el chat del producto anterior (cotización de cerramientos): va al agente de ventas.
  if (hash === "#/venta" || hash === "#/chat") return "venta";
  if (hash === "#/agente") return "agente";
  if (hash === "#/asistente") return "asistente";
  if (hash === "#/catalogo") return "catalogo";
  if (hash === "#/pedidos") return "pedidos";
  if (hash === "#/conversaciones") return "conversaciones";
  if (hash === "#/login") return "login";
  if (hash === "#/signup") return "signup";
  return "oportunidades";
}

export default function App() {
  const hash = useHashRoute();
  // La tienda pública de un negocio es la vista del cliente: sin panel ni menú. Una instancia por
  // tienda: al cambiar de tienda se desmonta la anterior y se descartan sus respuestas pendientes.
  const store = /^#\/tienda\/([a-z0-9-]{3,48})$/.exec(hash);
  if (store) return <Store key={store[1]} slug={store[1]} />;
  return <Backoffice hash={hash} />;
}

function Backoffice({ hash }: { hash: string }) {
  const [health, setHealth] = useState<Health | null>(null);
  const { status } = useSession();
  const active = sectionFor(hash);

  useEffect(() => {
    let alive = true;
    api
      .health()
      .then((h) => {
        if (alive) setHealth(h);
      })
      .catch(() => {
        if (alive) setHealth(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  // Con sesión, login/registro no tienen sentido: al panel.
  useEffect(() => {
    if (status === "ready" && (active === "login" || active === "signup")) {
      window.location.hash = "#/oportunidades";
    }
  }, [status, active]);

  // Sin sesión, login y registro se muestran solos (sin el menú del panel, que no se puede usar).
  if (status === "signed_out" && active !== "venta") {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <div className="auth-brand"><Mark /> <b>Presupuesto Vivo</b></div>
          {active === "signup" ? <Signup /> : <Login />}
        </div>
      </main>
    );
  }

  return (
    <Shell health={health} active={active}>
      {active === "venta" ? (
        <Sales health={health} />
      ) : (
        <Panel active={active} health={health} />
      )}
    </Shell>
  );
}

/** Secciones que dependen de la cuenta: login, registro y el panel del negocio. */
function Panel({ active, health }: { active: Section; health: Health | null }) {
  const { status, retry, signOut } = useSession();

  if (status === "unconfigured") {
    return (
      <Notice title="Cuentas sin configurar" pill="Configuración">
        Faltan <code>VITE_SUPABASE_URL</code> y <code>VITE_SUPABASE_ANON_KEY</code> en <code>web/.env</code>{" "}
        (ver <code>.env.example</code>). Mientras tanto podés usar el Chat demo.
      </Notice>
    );
  }
  if (status === "loading") return <Notice title="Cargando tu negocio…" />;
  if (status === "signed_out") return active === "signup" ? <Signup /> : <Login />;
  if (status === "no_business") {
    return (
      <Notice title="Tu cuenta no tiene un negocio asociado" pill="Sin negocio">
        No encontramos un negocio para esta cuenta. Escribinos para revisarlo.
        <br />
        <button className="btn sm" type="button" style={{ marginTop: 12 }} onClick={() => void signOut()}>
          Cerrar sesión
        </button>
      </Notice>
    );
  }
  if (status === "error") {
    return (
      <Notice title="Sin conexión con la API" pill="Sin conexión">
        No pude cargar tu negocio. ¿Está corriendo el backend?
        <br />
        <button className="btn sm" type="button" style={{ marginTop: 12 }} onClick={retry}>
          Reintentar
        </button>
      </Notice>
    );
  }
  if (active === "agente") return <AgentSetup />;
  if (active === "asistente") return <AgentWizard health={health} />;
  if (active === "catalogo") return <Catalog />;
  if (active === "pedidos") return <OrdersPage />;
  if (active === "conversaciones") return <Inbox />;
  return <Opportunities />;
}

function Notice({ title, pill, children }: { title: string; pill?: string; children?: React.ReactNode }) {
  return (
    <div className="sheet">
      <div className="titlebar">
        <h1>{title}</h1>
      </div>
      {children && (
        <div className="state err" role="status">
          {pill && (
            <>
              <span className="pill neg">{pill}</span>
              <br />
            </>
          )}
          {children}
        </div>
      )}
    </div>
  );
}
