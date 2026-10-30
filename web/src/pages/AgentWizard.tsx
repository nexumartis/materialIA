import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api, type AgentProfile, type Health, type ImportResult, type Me } from "../lib/api";
import { downloadTemplate } from "./Catalog";
import { EvalsSection, PoliciesSection } from "./AgentAdvanced";

const TONES: { key: AgentProfile["tone"]; label: string; sample: string }[] = [
  { key: "cercano", label: "Cercano", sample: "¡Hola! ¿Qué estás buscando? Te ayudo." },
  { key: "profesional", label: "Profesional", sample: "Hola, ¿en qué te puedo ayudar?" },
  { key: "formal", label: "Formal", sample: "Buenos días, ¿en qué puedo ayudarle?" },
];

const STEPS = ["Negocio", "Rubro", "Catálogo", "Cómo habla", "Políticas", "Cobro", "Probar", "Publicar"] as const;
const MAX_PREVIEW = 12;   // igual que MAX_PREVIEW_MESSAGES del backend
const SLUG = /^[a-z0-9-]{3,48}$/;

/** Lo que el asistente edita: NADA se guarda en el servidor hasta «Publicar» (una sola versión). */
type Draft = Pick<AgentProfile, "business_type" | "public_slug" | "seller_name" | "tone" | "greeting" | "shipping"
  | "hours" | "payment_methods" | "policies" | "faq" | "rules" | "disabled_tools">;

function draftOf(p: AgentProfile): Draft {
  const { business_type, public_slug, seller_name, tone, greeting, shipping, hours, payment_methods, policies, faq,
    rules, disabled_tools } = p;
  return { business_type, public_slug, seller_name, tone, greeting, shipping, hours, payment_methods, policies, faq,
    rules, disabled_tools };
}

/** Lo que se prueba: sin el link (se edita en el paso 1 y no cambia cómo responde). */
function testable(d: Draft): Partial<AgentProfile> {
  const { public_slug: _ignored, ...rest } = d;
  return rest;
}

// Borrador, paso y pasos recorridos viven en este navegador (comodidad: perderlos no rompe nada).
// `basedOn`: versión guardada sobre la que se armó el borrador; si el perfil cambió desde otro
// lado, el borrador viejo se descarta para no pisar esos cambios al publicar.
interface Local { step: number; draft: Draft | null; basedOn: string | null; visited: number[]; publishedFor: string | null }
const storeKey = (tenant: string) => `pv.asistente.${tenant}`;
function loadLocal(tenant: string): Local {
  try {
    const v = JSON.parse(localStorage.getItem(storeKey(tenant)) ?? "null");
    return { step: Number(v?.step) || 0, draft: v?.draft ?? null, basedOn: v?.basedOn ?? null,
      visited: Array.isArray(v?.visited) ? v.visited : [], publishedFor: v?.publishedFor ?? null };
  } catch {
    return { step: 0, draft: null, basedOn: null, visited: [], publishedFor: null };
  }
}
function saveLocal(tenant: string, local: Local) {
  try {
    localStorage.setItem(storeKey(tenant), JSON.stringify(local));
  } catch {
    /* almacenamiento no disponible */
  }
}

/** Crear el agente paso a paso: negocio, rubro, catálogo, cómo habla, políticas, cobro, probar y publicar. */
export function AgentWizard({ health }: { health: Health | null }) {
  const [me, setMe] = useState<Me | null>(null);
  const [profile, setProfile] = useState<AgentProfile | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<{ key: string; label: string }[]>([]);
  const [products, setProducts] = useState<number | null>(null);
  const [tested, setTested] = useState(false);
  const [visited, setVisited] = useState<number[]>([]);
  const [publishedFor, setPublishedFor] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.me(), api.agentProfile()])
      .then(([m, p]) => {
        setMe(m);
        setProfile(p);
        const local = loadLocal(m.tenant_id);
        const fresh = !local.draft || local.basedOn !== p.updated_at;
        if (local.draft && fresh) setNotice("Tu agente cambió desde que dejaste el asistente: seguimos desde lo guardado.");
        setDraft(fresh ? draftOf(p) : local.draft);
        setStep(Math.min(local.step, STEPS.length - 1));
        setVisited(local.visited);
        setPublishedFor(local.publishedFor);
      })
      .catch(() => setError("No pude cargar tu agente."));
    api.agentTemplates().then(setTemplates).catch(() => {});
    api.catalog().then((c) => setProducts(c.length)).catch(() => setProducts(0));
  }, []);

  useEffect(() => {
    if (me && profile) saveLocal(me.tenant_id, { step, draft, basedOn: profile.updated_at, visited, publishedFor });
  }, [me, profile, step, draft, visited, publishedFor]);

  const done = useMemo<boolean[]>(() => {
    if (!draft || !profile) return STEPS.map(() => false);
    // Lo que el sistema completa solo (link, rubro, nombre) cuenta recién cuando el dueño pasó por el paso.
    const saw = (i: number) => visited.includes(i);
    return [
      saw(0) && SLUG.test(draft.public_slug),
      saw(1),
      (products ?? 0) > 0,
      saw(3) && !!draft.seller_name && !!draft.greeting,
      !!draft.shipping || !!draft.hours,
      !!draft.payment_methods,
      tested,
      publishedFor === profile.updated_at && JSON.stringify(draftOf(profile)) === JSON.stringify(draft),
    ];
  }, [draft, profile, products, tested, visited, publishedFor]);

  if (!draft || !profile || !me) {
    return <div className="sheet"><div className={`state${error ? " err" : ""}`}>{error ?? "Cargando…"}</div></div>;
  }
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setDraft({ ...draft, [k]: v });
  const go = (n: number) => {
    setError(null);
    setVisited((v) => (v.includes(step) ? v : [...v, step]));
    setStep(Math.max(0, Math.min(STEPS.length - 1, n)));
  };

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Crear mi agente</h1>
          <p className="finding">Ocho pasos para dejar tu vendedor virtual listo. Podés salir y volver: se guarda tu avance en este navegador.</p>
        </div>
        <div className="right"><a className="btn sm ghost" href="#/agente">Ajustes avanzados</a></div>
      </div>

      <ol className="wizard-steps" aria-label="Pasos">
        {STEPS.map((s, i) => (
          <li key={s}>
            <button type="button" className={`wizard-step${i === step ? " current" : ""}${done[i] ? " done" : ""}`}
              aria-current={i === step ? "step" : undefined} onClick={() => go(i)}>
              <span className="wizard-num">{done[i] ? "✓" : i + 1}</span> {s}
            </button>
          </li>
        ))}
      </ol>
      <p className="muted small" aria-live="polite">{done.filter(Boolean).length} de {STEPS.length} pasos listos</p>

      {notice && <div className="state" role="status">{notice}</div>}
      {error && <div className="state err" role="alert">{error}</div>}

      <section className="setup-card wizard-card" aria-label={STEPS[step]}>
        {step === 0 && (
          <>
            <h2 className="panel-title">1. Tu negocio</h2>
            <p className="muted">Negocio: <b>{me.business_name}</b></p>
            <label className="field">
              <span>Link de tu tienda</span>
              <div className="inline">
                <span className="prefix">…#/tienda/</span>
                <input value={draft.public_slug} onChange={(e) => set("public_slug", e.target.value.toLowerCase())}
                  aria-label="Link de tu tienda" />
              </div>
              <small>Es lo que vas a compartir con tus clientes. De 3 a 48 minúsculas, números y guiones.</small>
              {!SLUG.test(draft.public_slug) && <small className="neg-text">Revisá el link: así no se puede publicar.</small>}
            </label>
          </>
        )}

        {step === 1 && (
          <RubroStep templates={templates} current={draft.business_type}
            onApplied={(t) => setDraft({ ...draft, ...t })} onError={setError} />
        )}

        {step === 2 && <CatalogStep products={products} onImported={(n) => setProducts(n)} onError={setError} />}

        {step === 3 && (
          <>
            <h2 className="panel-title">4. Cómo habla</h2>
            <div className="grid2">
              <label className="field">
                <span>Nombre del vendedor</span>
                <input value={draft.seller_name} maxLength={40} onChange={(e) => set("seller_name", e.target.value)} />
              </label>
              <label className="field">
                <span>Tono</span>
                <select value={draft.tone} onChange={(e) => set("tone", e.target.value as AgentProfile["tone"])}>
                  {TONES.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
                </select>
                <small>Ejemplo: «{TONES.find((t) => t.key === draft.tone)?.sample}»</small>
              </label>
            </div>
            <label className="field">
              <span>Saludo</span>
              <textarea rows={2} maxLength={400} value={draft.greeting} onChange={(e) => set("greeting", e.target.value)} />
            </label>
          </>
        )}

        {step === 4 && (
          <>
            <h2 className="panel-title">5. Políticas</h2>
            <p className="muted">Lo que el agente responde sobre envíos y horarios. Las reglas de abajo las hace cumplir el sistema, no el modelo.</p>
            <div className="grid2">
              <label className="field">
                <span>Envíos y entregas</span>
                <textarea rows={2} value={draft.shipping} onChange={(e) => set("shipping", e.target.value)} placeholder="Ej.: CABA y GBA, costo según zona" />
              </label>
              <label className="field">
                <span>Horarios y retiro</span>
                <textarea rows={2} value={draft.hours} onChange={(e) => set("hours", e.target.value)} placeholder="Ej.: Lunes a viernes 8 a 18" />
              </label>
            </div>
            <PoliciesSection policies={draft.policies ?? {}} onChange={(v) => set("policies", v)} />
          </>
        )}

        {step === 5 && (
          <>
            <h2 className="panel-title">6. Cobro</h2>
            <label className="field">
              <span>Medios de pago que aceptás</span>
              <input value={draft.payment_methods} onChange={(e) => set("payment_methods", e.target.value)}
                placeholder="Ej.: transferencia, Mercado Pago, efectivo al retirar" />
            </label>
            <ul className="wizard-notes">
              <li>
                Link de pago: {!health?.payments
                  ? "no pude consultar qué medio está activo."
                  : health.payments.provider === "mercadopago"
                    ? "Mercado Pago (cobro verificado con el proveedor)."
                    : "en modo de prueba (simulado): no cobra dinero real."}
              </li>
              <li>Transferencias: el cliente adjunta el comprobante en el chat y vos confirmás el pago en <a href="#/pedidos">Pedidos</a> después de verlo en tu banco. Un comprobante solo nunca marca un pedido como pagado.</li>
            </ul>
          </>
        )}

        {step === 6 && <PreviewStep draft={draft} onTested={() => setTested(true)} />}

        {step === 7 && (
          <PublishStep draft={draft} profile={profile} done={done}
            onPublished={(p) => { setProfile(p); setDraft(draftOf(p)); setPublishedFor(p.updated_at); setNotice(null); }}
            onGo={go} />
        )}
      </section>

      <div className="setup-actions">
        <button className="btn" type="button" disabled={step === 0} onClick={() => go(step - 1)}>Anterior</button>
        {step < STEPS.length - 1 && (
          <button className="btn primary" type="button" onClick={() => go(step + 1)}>Siguiente</button>
        )}
      </div>
    </div>
  );
}

function RubroStep({ templates, current, onApplied, onError }: {
  templates: { key: string; label: string }[];
  current: string;
  onApplied: (t: Partial<Draft>) => void;
  onError: (m: string) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  async function apply(key: string) {
    if (!window.confirm("En tu borrador se reemplazan el nombre del vendedor, el tono, el saludo, las preguntas "
      + "frecuentes y las reglas por los del rubro. Envíos, horarios y medios de pago no cambian. No se publica "
      + "nada hasta el último paso. ¿Seguimos?")) return;
    setBusy(key);
    try {
      onApplied(await api.agentTemplate(key));
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "No pude cargar la plantilla.");
    } finally {
      setBusy(null);
    }
  }
  return (
    <>
      <h2 className="panel-title">2. Rubro</h2>
      <p className="muted">Elegí el más parecido: precarga cómo habla y preguntas frecuentes de ejemplo en tu borrador. Después lo ajustás.</p>
      <div className="wizard-options">
        {templates.map((t) => (
          <button key={t.key} type="button" className={`wizard-option${t.key === current ? " on" : ""}`}
            aria-pressed={t.key === current} disabled={busy !== null} onClick={() => void apply(t.key)}>
            {busy === t.key ? "Cargando…" : t.label}
          </button>
        ))}
      </div>
    </>
  );
}

function CatalogStep({ products, onImported, onError }: {
  products: number | null;
  onImported: (n: number) => void;
  onError: (m: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  async function onFile(file: File) {
    setBusy(true);
    setResult(null);
    try {
      setResult(await api.importCatalog(await file.text()));
      onImported((await api.catalog()).length);
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "No pude importar el archivo.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h2 className="panel-title">3. Catálogo</h2>
      <p className="muted">
        Tu agente sólo ofrece lo que está acá, con precio y stock reales. Hoy tenés <b>{products ?? "…"}</b> productos.
      </p>
      <div className="inline">
        <button className="btn sm ghost" type="button" onClick={downloadTemplate}>Descargar plantilla CSV</button>
        <label className={`btn sm primary${busy ? " disabled" : ""}`}>
          {busy ? "Importando…" : "Subir CSV"}
          <input type="file" accept=".csv,text/csv" hidden disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) void onFile(f);
            }} />
        </label>
        <a className="btn sm ghost" href="#/catalogo">Ver y editar productos</a>
      </div>
      {result && (
        <div className="import-result" role="status">
          <span className="pill pos">{result.created} nuevos</span>
          <span className="pill neu">{result.updated} actualizados</span>
          {result.errors.length > 0 && <span className="pill neg">{result.errors.length} con error</span>}
          {result.errors.length > 0 && (
            <ul>{result.errors.map((e) => <li key={e.fila}>Fila {e.fila}{e.sku ? ` (${e.sku})` : ""}: {e.error}</li>)}</ul>
          )}
        </div>
      )}
      <p className="note">Conectar Tiendanube o Mercado Libre todavía no está disponible.</p>
    </>
  );
}

/** Chat de vista previa con el BORRADOR: una conversación de prueba en el servidor, mensaje a
 *  mensaje, sin guardar el perfil. Se borra al reiniciar o al salir del paso. */
function PreviewStep({ draft, onTested }: { draft: Draft; onTested: () => void }) {
  const [conv, setConv] = useState<string | null>(null);
  const [turns, setTurns] = useState<{ message: string; reply: string; mode: string }[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const convRef = useRef<string | null>(null);
  convRef.current = conv;

  useEffect(() => () => {
    if (convRef.current) void api.endPreview(convRef.current).catch(() => {});
  }, []);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || busy || turns.length >= MAX_PREVIEW) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.agentPreview(msg, conv, testable(draft));
      setConv(r.conversation_id);
      setTurns((t) => [...t, { message: msg, reply: r.reply, mode: r.mode }]);
      setInput("");
      onTested();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No pude probar el agente.");
    } finally {
      setBusy(false);
    }
  }

  function restart() {
    if (conv) void api.endPreview(conv).catch(() => {});
    setConv(null);
    setTurns([]);
    setError(null);
  }

  const full = turns.length >= MAX_PREVIEW;
  return (
    <>
      <h2 className="panel-title">7. Probar</h2>
      <p className="muted">Escribile como si fueras un cliente. Usa lo que configuraste, aunque todavía no lo publicaste. No crea pedidos ni aparta stock.</p>
      <div className="chatlog wizard-preview" aria-label="Vista previa">
        {turns.length === 0 && <div className="bubble bot">{draft.greeting || "Escribí un mensaje para empezar."}</div>}
        {turns.map((t, i) => (
          <div key={i}>
            <div className="msg me"><div className="bubble me">{t.message}</div></div>
            <div className="msg bot">
              {/* Honestidad: sin modelo configurado responde por reglas, y se dice. */}
              {t.mode === "mock" && <span className="msg-author">Respuesta por reglas (sin IA)</span>}
              <div className="bubble bot">{t.reply}</div>
            </div>
          </div>
        ))}
        {busy && <div className="bubble bot typing">Escribiendo…</div>}
      </div>
      <div className="quick">
        {["Hola", "¿Qué productos tenés?", "¿Hacen envíos?", "¿Cómo pago?"].map((s) => (
          <button key={s} type="button" className="chip" disabled={busy || full} onClick={() => void send(s)}>{s}</button>
        ))}
      </div>
      <form className="composer" onSubmit={(e) => { e.preventDefault(); void send(input); }}>
        <input type="text" aria-label="Mensaje de prueba" autoComplete="off" value={input} maxLength={1000}
          disabled={full} placeholder={full ? "Límite de la vista previa: reiniciala" : "Escribí como cliente…"}
          onChange={(e) => setInput(e.target.value)} />
        <button className="btn primary" type="submit" disabled={busy || !input.trim() || full}>Enviar</button>
        <button className="btn" type="button" disabled={busy || turns.length === 0} onClick={restart}>Reiniciar</button>
      </form>
      {error && <div className="state err" role="alert">{error}</div>}
      <EvalsSection draft={() => testable(draft)} />
    </>
  );
}

function PublishStep({ draft, profile, done, onPublished, onGo }: {
  draft: Draft;
  profile: AgentProfile;
  done: boolean[];
  onPublished: (p: AgentProfile) => void;
  onGo: (n: number) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [blocked, setBlocked] = useState(false);
  const storeUrl = `${window.location.origin}${window.location.pathname}#/tienda/${profile.public_slug}`;
  const missing = STEPS.slice(0, 6).map((s, i) => ({ s, i })).filter(({ i }) => !done[i]);

  async function publish(requireEvals: boolean) {
    setBusy(true);
    setMsg(null);
    setBlocked(false);
    try {
      onPublished(await api.saveAgentProfile({ ...draft, require_evals: requireEvals }));
      setMsg({ ok: true, text: "¡Publicado! Tu agente ya atiende así." });
    } catch (e) {
      setBlocked(e instanceof ApiError && e.code === "evals_failed");
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : "No pude publicar." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2 className="panel-title">8. Publicar</h2>
      {missing.length > 0 ? (
        <div className="wizard-notes">
          <p className="muted">Te falta:</p>
          <ul>{missing.map(({ s, i }) => <li key={s}><button className="linkish" type="button" onClick={() => onGo(i)}>{s}</button></li>)}</ul>
        </div>
      ) : (
        <p className="muted">Todo listo. Al publicar, tu agente empieza a responder con lo que configuraste.</p>
      )}
      <div className="inline">
        <button className="btn primary" type="button" disabled={busy} onClick={() => void publish(true)}>
          {busy ? "Publicando…" : "Publicar"}
        </button>
        {blocked && (
          <button className="btn ghost" type="button" disabled={busy} onClick={() => void publish(false)}>Publicar igual</button>
        )}
        {msg && <span className={`pill ${msg.ok ? "pos" : "neg"}`} role="status">{msg.text}</span>}
      </div>
      <h3 className="sub">Compartí tu tienda</h3>
      <div className="inline">
        <code className="wizard-url">{storeUrl}</code>
        <button className="btn sm ghost" type="button" onClick={() => void navigator.clipboard?.writeText(storeUrl)}>Copiar link</button>
        <a className="btn sm" href={storeUrl} target="_blank" rel="noopener noreferrer">Abrir mi tienda</a>
      </div>
      <p className="note">WhatsApp todavía no está disponible para conectar.</p>
    </>
  );
}
