import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  api,
  type AgentProfile,
  type AiUsage,
  type EvalCase,
  type EvalRun,
  type KnowledgeDoc,
  type Policies,
  type ProfileVersion,
} from "../lib/api";

const errText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);
const list = (v?: string[]) => (v ?? []).join(", ");
const parse = (v: string) => v.split(",").map((x) => x.trim()).filter(Boolean);

/** Reglas que el CÓDIGO hace cumplir (no dependen de que el modelo las respete). */
export function PoliciesSection({ policies, onChange }: { policies: Policies; onChange: (p: Policies) => void }) {
  return (
    <section className="setup-card">
      <h2 className="panel-title">Políticas del negocio</h2>
      <p className="panel-sub">Las hace cumplir el sistema, no la IA: aunque el cliente insista, no se saltean.</p>
      <div className="grid2">
        <label className="field">
          <span>Compra mínima ($)</span>
          <input
            inputMode="decimal"
            value={policies.min_order_total ?? ""}
            placeholder="Sin mínimo"
            onChange={(e) => onChange({ ...policies, min_order_total: e.target.value ? Number(e.target.value) : undefined })}
          />
        </label>
        <label className="field">
          <span>Zonas de envío (separadas por coma)</span>
          <input
            value={list(policies.delivery_zones)}
            placeholder="Ej.: CABA, GBA, Rosario"
            onChange={(e) => onChange({ ...policies, delivery_zones: parse(e.target.value) })}
          />
        </label>
      </div>
      <label className="field">
        <span>Categorías que vende sólo una persona (separadas por coma)</span>
        <input
          value={list(policies.human_only_categories)}
          placeholder="Ej.: sanitarios, a medida"
          onChange={(e) => onChange({ ...policies, human_only_categories: parse(e.target.value) })}
        />
      </label>
    </section>
  );
}

export function ToolsSection({ disabled, onChange }: { disabled: string[]; onChange: (d: string[]) => void }) {
  const [tools, setTools] = useState<{ key: string; label: string }[]>([]);
  useEffect(() => {
    api.agentTools().then(setTools).catch(() => {});
  }, []);
  return (
    <section className="setup-card">
      <h2 className="panel-title">Qué puede hacer tu agente</h2>
      <p className="panel-sub">Buscar productos, consultar stock y armar el carrito están siempre activos.</p>
      <div className="checks">
        {tools.map((t) => (
          <label key={t.key} className="check">
            <input
              type="checkbox"
              checked={!disabled.includes(t.key)}
              onChange={(e) => onChange(e.target.checked ? disabled.filter((x) => x !== t.key) : [...disabled, t.key])}
            />
            {t.label}
          </label>
        ))}
      </div>
    </section>
  );
}

/** Documentos largos (garantías, instalación, fichas) que el agente consulta cuando los necesita. */
export function KnowledgeSection() {
  const [docs, setDocs] = useState<KnowledgeDoc[] | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    api.knowledge().then(setDocs).catch(() => setDocs([]));
  }, []);
  useEffect(load, [load]);

  async function add() {
    setMsg(null);
    try {
      await api.addKnowledge(title, text);
      setTitle("");
      setText("");
      load();
    } catch (e) {
      setMsg(errText(e, "No pude guardar el documento."));
    }
  }

  return (
    <section className="setup-card">
      <h2 className="panel-title">Documentos del negocio</h2>
      <p className="panel-sub">Garantías, instalación, fichas técnicas, políticas de cambio. El agente busca acá cuando le preguntan.</p>
      {docs?.map((d) => (
        <div className="faq-row" key={d.id}>
          <span><b>{d.title}</b> <span className="muted">{Math.round(d.chars / 1000)}k caracteres · {d.chunks} fragmentos</span></span>
          <button className="btn sm ghost" type="button" onClick={() => void api.deleteKnowledge(d.id).then(load)} aria-label={`Borrar ${d.title}`}>✕</button>
        </div>
      ))}
      <label className="field">
        <span>Título</span>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ej.: Garantía de grifería" />
      </label>
      <label className="field">
        <span>Contenido (pegalo o subí un .txt / .md)</span>
        <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      <div className="inline">
        <label className="btn sm ghost">
          Subir archivo
          <input
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
            hidden
            onChange={async (e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (!f) return;
              setText(await f.text());
              if (!title) setTitle(f.name.replace(/\.(txt|md)$/i, ""));
            }}
          />
        </label>
        <button className="btn sm primary" type="button" disabled={!title.trim() || !text.trim()} onClick={() => void add()}>
          Agregar documento
        </button>
        {msg && <span className="pill neg">{msg}</span>}
      </div>
    </section>
  );
}

/** Pruebas del agente: se corren sobre el borrador antes de guardar. */
export function EvalsSection({ draft }: { draft: () => Partial<AgentProfile> }) {
  const [cases, setCases] = useState<EvalCase[] | null>(null);
  const [message, setMessage] = useState("");
  const [contains, setContains] = useState("");
  const [notContains, setNotContains] = useState("");
  const [run, setRun] = useState<EvalRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    api.evalCases().then(setCases).catch(() => setCases([]));
  }, []);
  useEffect(load, [load]);

  async function add() {
    setMsg(null);
    try {
      await api.addEvalCase({ message, expect_contains: parse(contains), expect_not_contains: parse(notContains) });
      setMessage("");
      setContains("");
      setNotContains("");
      load();
    } catch (e) {
      setMsg(errText(e, "No pude agregar el caso."));
    }
  }

  async function test() {
    setBusy(true);
    setMsg(null);
    try {
      setRun(await api.runEvals(draft()));
    } catch (e) {
      setMsg(errText(e, "No pude correr las pruebas."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="setup-card">
      <h2 className="panel-title">Pruebas del agente</h2>
      <p className="panel-sub">Mensajes de cliente y qué tiene que (o no) responder. Si hay pruebas, “Guardar” no activa una versión que las falle.</p>
      {cases?.map((c) => {
        const r = run?.results.find((x) => x.id === c.id);
        return (
          <div className="eval-row" key={c.id}>
            <div>
              <code>{c.message.split("\n").join(" → ")}</code>
              <div className="muted small">
                {c.expect_contains.length > 0 && <>debe decir: {c.expect_contains.join(", ")} </>}
                {c.expect_not_contains.length > 0 && <>· no debe decir: {c.expect_not_contains.join(", ")}</>}
              </div>
              {r && !r.passed && <div className="small neg-text">{r.failures.join(" · ")} — respondió: “{r.reply.slice(0, 160)}”</div>}
            </div>
            <div className="inline">
              {r && <span className={`pill ${r.passed ? "pos" : "neg"}`}>{r.passed ? "pasa" : "falla"}</span>}
              <button className="btn sm ghost" type="button" onClick={() => void api.deleteEvalCase(c.id).then(load)} aria-label="Borrar caso">✕</button>
            </div>
          </div>
        );
      })}
      <div className="grid2">
        <label className="field">
          <span>Mensaje del cliente (una línea por mensaje)</span>
          <textarea rows={2} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="¿Hacen envíos a Rosario?" />
        </label>
        <div>
          <label className="field">
            <span>Tiene que decir (separado por coma)</span>
            <input value={contains} onChange={(e) => setContains(e.target.value)} placeholder="Rosario" />
          </label>
          <label className="field">
            <span>No tiene que decir</span>
            <input value={notContains} onChange={(e) => setNotContains(e.target.value)} placeholder="gratis" />
          </label>
        </div>
      </div>
      <div className="inline">
        <button className="btn sm" type="button" disabled={!message.trim()} onClick={() => void add()}>+ Agregar prueba</button>
        <button className="btn sm primary" type="button" disabled={busy || !cases?.length} onClick={() => void test()}>
          {busy ? "Probando…" : "Probar con los cambios sin guardar"}
        </button>
        {run && <span className={`pill ${run.passed === run.total ? "pos" : "neg"}`}>{run.passed}/{run.total} pasan</span>}
        {msg && <span className="pill neg">{msg}</span>}
      </div>
    </section>
  );
}

export function VersionsSection({ current, onRestored }: { current: number; onRestored: (p: AgentProfile) => void }) {
  const [versions, setVersions] = useState<ProfileVersion[] | null>(null);
  useEffect(() => {
    api.profileVersions().then(setVersions).catch(() => setVersions([]));
  }, [current]);

  async function restore(v: number) {
    if (!window.confirm(`Volver a la versión ${v}? Se crea una versión nueva con esa configuración.`)) return;
    onRestored(await api.restoreVersion(v));
  }

  return (
    <section className="setup-card">
      <h2 className="panel-title">Versiones</h2>
      <p className="panel-sub">Cada vez que guardás se crea una versión. Cada respuesta del agente queda registrada con la versión que la generó.</p>
      {versions?.map((v) => (
        <div className="faq-row" key={v.version}>
          <span>
            <b>v{v.version}</b> <span className="muted">{new Date(v.created_at).toLocaleString("es-AR")} · {v.seller_name} · {v.tone}</span>
          </span>
          {v.version === current ? (
            <span className="pill pos">vigente</span>
          ) : (
            <button className="btn sm ghost" type="button" onClick={() => void restore(v.version)}>Volver a esta</button>
          )}
        </div>
      ))}
    </section>
  );
}

const KIND_LABEL: Record<string, string> = { venta: "Atención a clientes", resumen: "Resúmenes", memoria: "Memoria de clientes", otro: "Otros" };

/** Llamadas y tokens de IA del negocio en los últimos 30 días (costo sólo si está configurado). */
export function AiUsageSection() {
  const [u, setU] = useState<AiUsage | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api.aiUsage().then(setU).catch(() => setFailed(true));
  }, []);
  const n = (x: number) => x.toLocaleString("es-AR");
  return (
    <section className="setup-card">
      <h2 className="panel-title">Uso de IA (últimos 30 días)</h2>
      {failed ? <p className="muted">No pude cargar el uso.</p> : !u ? <p className="muted">Cargando…</p> : u.calls === 0 ? (
        <p className="muted">Todavía no hubo llamadas al modelo (o el agente responde por reglas, sin IA).</p>
      ) : (
        <>
          <div className="kv">
            {u.by_kind.map((k) => (
              <div className="row" key={k.kind}>
                <span className="k">{KIND_LABEL[k.kind] ?? k.kind}</span>
                <span className="v">{n(k.calls)} llamadas · {n(k.prompt_tokens + k.completion_tokens)} tokens</span>
              </div>
            ))}
            <div className="row">
              <span className="k"><b>Total</b></span>
              <span className="v">{n(u.calls)} llamadas · {n(u.prompt_tokens + u.completion_tokens)} tokens</span>
            </div>
          </div>
          <p className="note">
            {u.cost != null ? `Costo estimado: ${u.currency} ${u.cost.toLocaleString("es-AR")}.`
              : "Sin precio por token configurado en el servidor: se muestra el uso, no un costo."}
          </p>
        </>
      )}
    </section>
  );
}
