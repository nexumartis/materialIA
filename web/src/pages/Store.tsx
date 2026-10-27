import { useEffect, useMemo, useState } from "react";
import { ApiError, api, resetBuyerKey, type StoreInfo } from "../lib/api";
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
        storageKey: `pv.tienda.${slug}.conversacion`,
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
        <>
          <Sales health={null} source={source} />
          <MemoryNotice slug={slug} />
        </>
      ) : (
        <div className="sheet">
          <div className="state">Cargando…</div>
        </div>
      )}
    </div>
  );
}

/** Aviso de memoria: qué recuerda la tienda y cómo borrarlo. */
function MemoryNotice({ slug }: { slug: string }) {
  const [done, setDone] = useState(false);
  async function forget() {
    if (!window.confirm("Se borra lo que esta tienda recuerda de vos en este navegador. ¿Seguimos?")) return;
    try {
      await api.forgetMe(slug);
    } finally {
      resetBuyerKey();
      setDone(true);
    }
  }
  return (
    <p className="memory-note">
      {done ? (
        "Listo: esta tienda ya no recuerda tus preferencias."
      ) : (
        <>
          Esta tienda recuerda tus preferencias en este navegador para atenderte mejor (nunca datos de pago).{" "}
          <button className="linkish" type="button" onClick={() => void forget()}>Olvidarme</button>
        </>
      )}
    </p>
  );
}
