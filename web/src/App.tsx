import { useEffect, useState } from "react";
import { api, type Company, type Health } from "./lib/api";
import { useSession } from "./lib/session";
import { Shell, type Section } from "./components/Shell";
import { Opportunities } from "./pages/Opportunities";
import { Chat } from "./pages/Chat";
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
  if (hash === "#/chat") return "chat";
  if (hash === "#/login") return "login";
  if (hash === "#/signup") return "signup";
  return "oportunidades";
}

export default function App() {
  // La empresa A/B sólo aplica al chat demo ("probar sin cuenta").
  const [company, setCompany] = useState<Company>("A");
  const [health, setHealth] = useState<Health | null>(null);
  const { status } = useSession();
  const active = sectionFor(useHashRoute());

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

  return (
    <Shell company={company} onCompany={setCompany} health={health} active={active}>
      {active === "chat" ? <Chat company={company} health={health} /> : <Panel active={active} />}
    </Shell>
  );
}

/** Secciones que dependen de la cuenta: login, registro y el panel del negocio. */
function Panel({ active }: { active: Section }) {
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
