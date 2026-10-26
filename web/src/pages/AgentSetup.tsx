import { useEffect, useState } from "react";
import { ApiError, api, type AgentProfile } from "../lib/api";

const TONES: { key: AgentProfile["tone"]; label: string }[] = [
  { key: "cercano", label: "Cercano (vos, cálido)" },
  { key: "profesional", label: "Profesional (vos, prolijo)" },
  { key: "formal", label: "Formal (usted)" },
];

/** "Mi agente": rubro con plantilla, cómo habla, qué responde y el link de la tienda. */
export function AgentSetup() {
  const [p, setP] = useState<AgentProfile | null>(null);
  const [templates, setTemplates] = useState<{ key: string; label: string }[]>([]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    api.agentProfile().then(setP).catch(() => setMsg({ ok: false, text: "No pude cargar tu agente." }));
    api.agentTemplates().then(setTemplates).catch(() => {});
  }, []);

  if (!p) return <div className="sheet"><div className="state">{msg?.text ?? "Cargando…"}</div></div>;

  const set = <K extends keyof AgentProfile>(k: K, v: AgentProfile[K]) => setP({ ...p, [k]: v });
  const storeUrl = `${window.location.origin}${window.location.pathname}#/tienda/${p.public_slug}`;

  async function save(body: Partial<AgentProfile> & { apply_template?: boolean }, okText: string) {
    setSaving(true);
    setMsg(null);
    try {
      setP(await api.saveAgentProfile(body));
      setMsg({ ok: true, text: okText });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : "No pude guardar." });
    } finally {
      setSaving(false);
    }
  }

  function applyTemplate(key: string) {
    if (!window.confirm("Se reemplazan nombre, tono, saludo, preguntas y reglas por los de la plantilla. ¿Seguimos?")) return;
    void save({ business_type: key, apply_template: true }, "Plantilla aplicada. Revisala y guardá tus cambios.");
  }

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Mi agente</h1>
          <p className="finding">Cómo se presenta y qué responde tu vendedor virtual. Precios y stock salen del catálogo.</p>
        </div>
      </div>

      <form
        className="setup"
        onSubmit={(e) => {
          e.preventDefault();
          void save(
            {
              seller_name: p.seller_name, tone: p.tone, greeting: p.greeting, faq: p.faq, rules: p.rules,
              shipping: p.shipping, hours: p.hours, payment_methods: p.payment_methods, public_slug: p.public_slug,
            },
            "Guardado. Tu agente ya responde así.",
          );
        }}
      >
        <section className="setup-card">
          <h2 className="panel-title">Tu tienda</h2>
          <label className="field">
            <span>Link público</span>
            <div className="inline">
              <span className="prefix">…#/tienda/</span>
              <input value={p.public_slug} onChange={(e) => set("public_slug", e.target.value)} />
            </div>
          </label>
          <div className="inline">
            <a className="btn sm" href={storeUrl} target="_blank" rel="noopener noreferrer">Abrir mi tienda</a>
            <button className="btn sm ghost" type="button" onClick={() => void navigator.clipboard?.writeText(storeUrl)}>
              Copiar link
            </button>
          </div>
        </section>

        <section className="setup-card">
          <h2 className="panel-title">Rubro y plantilla</h2>
          <label className="field">
            <span>Rubro</span>
            <select value={p.business_type} onChange={(e) => applyTemplate(e.target.value)} disabled={saving}>
              {templates.map((t) => (
                <option key={t.key} value={t.key}>{t.label}</option>
              ))}
            </select>
          </label>
          <p className="panel-sub">Cambiar el rubro precarga un nombre, tono, saludo y preguntas frecuentes de ejemplo.</p>
        </section>

        <section className="setup-card">
          <h2 className="panel-title">Cómo habla</h2>
          <div className="grid2">
            <label className="field">
              <span>Nombre del vendedor</span>
              <input value={p.seller_name} maxLength={40} onChange={(e) => set("seller_name", e.target.value)} />
            </label>
            <label className="field">
              <span>Tono</span>
              <select value={p.tone} onChange={(e) => set("tone", e.target.value as AgentProfile["tone"])}>
                {TONES.map((t) => (
                  <option key={t.key} value={t.key}>{t.label}</option>
                ))}
              </select>
            </label>
          </div>
          <label className="field">
            <span>Saludo</span>
            <textarea rows={2} maxLength={400} value={p.greeting} onChange={(e) => set("greeting", e.target.value)} />
          </label>
        </section>

        <section className="setup-card">
          <h2 className="panel-title">Lo que el agente puede responder</h2>
          <div className="grid2">
            <label className="field">
              <span>Envíos y entregas</span>
              <textarea rows={2} value={p.shipping} onChange={(e) => set("shipping", e.target.value)} placeholder="Ej.: CABA y GBA, costo según zona" />
            </label>
            <label className="field">
              <span>Horarios y retiro</span>
              <textarea rows={2} value={p.hours} onChange={(e) => set("hours", e.target.value)} placeholder="Ej.: Lunes a viernes 8 a 18" />
            </label>
          </div>
          <label className="field">
            <span>Medios de pago</span>
            <input value={p.payment_methods} onChange={(e) => set("payment_methods", e.target.value)} />
          </label>

          <h3 className="sub">Preguntas frecuentes</h3>
          {p.faq.map((f, i) => (
            <div className="faq-row" key={i}>
              <input placeholder="Pregunta" value={f.q} onChange={(e) => set("faq", p.faq.map((x, j) => (j === i ? { ...x, q: e.target.value } : x)))} />
              <textarea rows={2} placeholder="Respuesta" value={f.a} onChange={(e) => set("faq", p.faq.map((x, j) => (j === i ? { ...x, a: e.target.value } : x)))} />
              <button className="btn sm ghost" type="button" onClick={() => set("faq", p.faq.filter((_, j) => j !== i))} aria-label="Quitar pregunta">✕</button>
            </div>
          ))}
          <button className="btn sm" type="button" onClick={() => set("faq", [...p.faq, { q: "", a: "" }])}>+ Agregar pregunta</button>

          <h3 className="sub">Reglas del negocio</h3>
          {p.rules.map((r, i) => (
            <div className="faq-row" key={i}>
              <input value={r} onChange={(e) => set("rules", p.rules.map((x, j) => (j === i ? e.target.value : x)))} />
              <button className="btn sm ghost" type="button" onClick={() => set("rules", p.rules.filter((_, j) => j !== i))} aria-label="Quitar regla">✕</button>
            </div>
          ))}
          <button className="btn sm" type="button" onClick={() => set("rules", [...p.rules, ""])}>+ Agregar regla</button>
        </section>

        <div className="setup-actions">
          {msg && <span className={`pill ${msg.ok ? "pos" : "neg"}`}>{msg.text}</span>}
          <button className="btn primary" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button>
        </div>
      </form>
    </div>
  );
}
