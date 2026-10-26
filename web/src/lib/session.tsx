// Sesión global del panel. El negocio sale de /app/me (el backend lo deriva del JWT);
// el cliente nunca elige empresa. 401 en cualquier llamada => se cierra la sesión.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { ApiError, api, setAuth, type Me } from "./api";

export type SessionStatus =
  | "unconfigured" // faltan VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
  | "loading"
  | "signed_out"
  | "ready" // sesión + negocio
  | "no_business" // sesión válida sin negocio asociado (403)
  | "error"; // la API no respondió

interface SessionValue {
  status: SessionStatus;
  session: Session | null;
  me: Me | null;
  signOut: () => Promise<void>;
  retry: () => void;
}

const Ctx = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState<SessionStatus>(supabase ? "loading" : "unconfigured");
  const [attempt, setAttempt] = useState(0);

  const signOut = useCallback(async () => {
    await supabase?.auth.signOut();
  }, []);

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (!data.session) setStatus("signed_out");
    });
    const { data } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      if (!s) {
        setMe(null);
        setStatus("signed_out");
      }
    });
    return () => data.subscription.unsubscribe();
  }, []);

  // El cliente de la API toma el token vigente y avisa si el backend lo rechaza.
  useEffect(() => {
    setAuth(() => session?.access_token ?? null, () => void signOut());
  }, [session, signOut]);

  // Se recarga el negocio cuando cambia la PERSONA, no en cada refresh del token
  // (TOKEN_REFRESHED cada ~hora): así el panel no se desmonta ni pierde ediciones.
  const userId = session?.user.id ?? null;
  useEffect(() => {
    if (!userId) return;
    let alive = true;
    setStatus("loading");
    api
      .me()
      .then((m) => {
        if (!alive) return;
        setMe(m);
        setStatus("ready");
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 403) setStatus("no_business");
        else if (!(e instanceof ApiError && e.status === 401)) setStatus("error");
      });
    return () => {
      alive = false;
    };
  }, [userId, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return <Ctx.Provider value={{ status, session, me, signOut, retry }}>{children}</Ctx.Provider>;
}

export function useSession(): SessionValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession fuera de SessionProvider");
  return v;
}
