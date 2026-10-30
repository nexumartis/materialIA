import { useEffect, useRef, useState } from "react";
import { api } from "./api";

const EVERY_MS = 30_000;

/** Conversaciones derivadas que todavía nadie atiende (pidió una persona o necesita cotización y
 *  nadie tomó el control). Se relee cada 30 s y, si sube y el dueño activó los avisos de este
 *  navegador, muestra una notificación. Sólo con sesión del panel. */
export function usePendingHandoffs(enabled: boolean): number {
  const [count, setCount] = useState(0);
  const last = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const check = () =>
      api.inbox("derivadas").then((list) => {
        if (!alive) return;
        const n = list.filter((c) => !c.taken).length;
        if (last.current !== null && n > last.current && notificationsOn()) {
          new Notification("Un cliente necesita atención", {
            body: n === 1 ? "Hay 1 conversación derivada sin atender." : `Hay ${n} conversaciones derivadas sin atender.`,
            tag: "pv-derivadas",
          });
        }
        last.current = n;
        setCount(n);
      }).catch(() => {});
    check();
    const t = window.setInterval(check, EVERY_MS);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [enabled]);

  return count;
}

export function notificationsSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function notificationsOn(): boolean {
  return notificationsSupported() && Notification.permission === "granted";
}
