import { useEffect, useMemo, useState } from "react";
import { ApiError, api, type StoreInfo } from "../lib/api";
import { Sales, type ChatSource } from "./Sales";

/** Tienda pública de un negocio (`#/tienda/<slug>`): lo que ve el cliente, sin cuenta. */
export function Store({ slug }: { slug: string }) {
  const [info, setInfo] = useState<StoreInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setInfo(null);
    setError(null);
    api
      .store(slug)
      .then((s) => alive && setInfo(s))
      .catch((e) => {
        if (!alive) return;
        setError(e instanceof ApiError && e.status === 404 ? "Esta tienda no existe." : "No pude conectar con la tienda.");
      });
    return () => {
      alive = false;
    };
  }, [slug]);

  const source = useMemo<ChatSource | null>(
    () =>
      info && {
        title: info.name,
        subtitle: info.seller_name ? `Te atiende ${info.seller_name}, asistente virtual.` : "Asistente virtual.",
        greeting: info.greeting || `¡Hola! Soy el asistente virtual de ${info.name}. ¿En qué te ayudo?`,
        suggestions: ["¿Qué productos tenés?", "¿Hacen envíos?"],
        chat: (m, c) => api.storeChat(slug, m, c),
        conversation: (c) => api.storeConversation(slug, c),
        customerView: true,
      },
    [info, slug],
  );

  return (
    <div className="store">
      {error ? (
        <div className="sheet">
          <div className="state err">{error}</div>
        </div>
      ) : source ? (
        <Sales health={null} source={source} />
      ) : (
        <div className="sheet">
          <div className="state">Cargando…</div>
        </div>
      )}
    </div>
  );
}
