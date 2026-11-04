import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";
import { PageHeader } from "../components/ui";
import { WidgetInstallGuide } from "../components/WidgetInstallGuide";
import { WidgetPreview } from "../components/WidgetPreview";
import { api, type WidgetConfig, type WidgetInfo, type WidgetInstall } from "../lib/api";

const HEX = /^#[0-9a-fA-F]{6}$/;
const LABEL_MAX = 40;
const GREETING_MAX = 140;
const DELAY_MAX = 120;
const same = (a: WidgetConfig, b: WidgetConfig) => JSON.stringify(a) === JSON.stringify(b);

/** Contraste del texto blanco del botón sobre el color elegido (WCAG). */
function whiteContrast(hex: string): number {
  const ch = (i: number) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const l = 0.2126 * ch(1) + 0.7152 * ch(3) + 0.0722 * ch(5);
  return 1.05 / (l + 0.05);
}

/** Lo mismo que valida el backend, para avisar antes de guardar. */
function problem(c: WidgetConfig): string | null {
  if (!HEX.test(c.color)) return "El color tiene que ser un código como #2563eb.";
  if (!c.label.trim()) return "Escribí el texto del botón.";
  if (c.label.length > LABEL_MAX) return `El texto del botón admite hasta ${LABEL_MAX} caracteres.`;
  if (c.greeting.length > GREETING_MAX) return `El saludo admite hasta ${GREETING_MAX} caracteres.`;
  if (!Number.isInteger(c.greeting_delay_s) || c.greeting_delay_s < 0 || c.greeting_delay_s > DELAY_MAX)
    return `La demora del saludo va de 0 a ${DELAY_MAX} segundos.`;
  return null;
}

const rtf = new Intl.RelativeTimeFormat("es-AR", { numeric: "auto" });
/** "hace 5 minutos", "ayer"… */
function ago(iso: string): string {
  const s = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
  const abs = Math.abs(s);
  if (abs < 60) return "recién";
  if (abs < 3600) return rtf.format(Math.round(s / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(s / 3600), "hour");
  return rtf.format(Math.round(s / 86400), "day");
}

/** Chat en tu web: personalizar el botón, pegar el código una vez y ver dónde quedó instalado. */
export function WebChat() {
  const [data, setData] = useState<WidgetInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<WidgetConfig | null>(null);
  const [hexText, setHexText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // `keepDraft`: «Actualizar» trae instalaciones nuevas sin pisar lo que el dueño está editando.
  const load = useCallback((keepDraft = false) => {
    setError(null);
    return api.widget().then((d) => {
      setData(d);
      if (!keepDraft) { setDraft(d.config); setHexText(d.config.color); }
    }, (e) => setError(e instanceof Error ? e.message : "No pude cargar el chat de tu web."));
  }, []);
  useEffect(() => { void load(); }, [load]);

  const dirty = data != null && draft != null && !same(data.config, draft);
  // Avisar si se cierra la pestaña con cambios sin guardar.
  useEffect(() => {
    if (!dirty) return;
    const on = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", on);
    return () => window.removeEventListener("beforeunload", on);
  }, [dirty]);

  if (!data || !draft) {
    return (
      <div className="sheet">
        <Header />
        {error ? (
          <p className="state err" role="alert">
            {error}{" "}
            <button className="btn sm" type="button" onClick={() => void load()}>Reintentar</button>
          </p>
        ) : <div className="state">Cargando…</div>}
      </div>
    );
  }

  const set = (patch: Partial<WidgetConfig>) => { setDraft({ ...draft, ...patch }); setSaveMsg(null); };
  const invalid = problem(draft);
  const lowContrast = HEX.test(draft.color) && whiteContrast(draft.color) < 3;

  async function save() {
    if (!draft || invalid) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const r = await api.saveWidget(draft);
      setData((d) => (d ? { ...d, config: r.config, snippet: r.snippet } : d));
      setDraft(r.config);
      setHexText(r.config.color);
      setSaveMsg({ ok: true, text: "Guardado. Ya se ve así en tu web." });
    } catch (e) {
      setSaveMsg({ ok: false, text: e instanceof Error ? e.message : "No se pudo guardar." });
    } finally {
      setSaving(false);
    }
  }

  async function refresh() {
    setRefreshing(true);
    await load(true);
    setRefreshing(false);
  }

  const lastHost = data.installs[0]?.host ?? null;
  return (
    <div className="sheet">
      <Header />
      {error && <p className="state err" role="alert">{error}</p>}

      <section className="results-card wc-step" aria-labelledby="wc-s1">
        <h2 id="wc-s1"><span className="wc-n" aria-hidden>1</span> Personalizalo</h2>
        <div className="wc-custom">
          <form className="wc-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
            <div className="field">
              <label htmlFor="wc-color-hex">Color del botón</label>
              <span className="wc-color">
                <input type="color" aria-label="Elegir color" value={HEX.test(draft.color) ? draft.color : "#2563eb"}
                  onChange={(e) => { set({ color: e.target.value }); setHexText(e.target.value); }} />
                <input id="wc-color-hex" value={hexText} maxLength={7} spellCheck={false} autoComplete="off"
                  aria-invalid={!HEX.test(hexText)}
                  onChange={(e) => {
                    const v = e.target.value.trim();
                    setHexText(v);
                    set({ color: v.startsWith("#") ? v : `#${v}` });
                  }} />
              </span>
              {lowContrast && <small role="status">El texto blanco se lee poco sobre este color: probá uno más oscuro.</small>}
            </div>

            <label className="field">
              <span>Texto del botón</span>
              <input value={draft.label} maxLength={LABEL_MAX} required onChange={(e) => set({ label: e.target.value })} />
            </label>

            <fieldset className="wc-seg-wrap">
              <legend>Posición</legend>
              <div className="wc-seg">
                {(["right", "left"] as const).map((pos) => (
                  <label key={pos} className={draft.position === pos ? "on" : ""}>
                    <input type="radio" name="wc-pos" value={pos} checked={draft.position === pos}
                      onChange={() => set({ position: pos })} />
                    {pos === "right" ? "Derecha" : "Izquierda"}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="field">
              <label htmlFor="wc-greeting">Saludo automático</label>
              <textarea id="wc-greeting" rows={3} value={draft.greeting} maxLength={GREETING_MAX}
                placeholder="¿Buscás algo? Te ayudo a encontrarlo." aria-describedby="wc-greeting-help"
                onChange={(e) => set({ greeting: e.target.value })} />
              <small id="wc-greeting-help" className="wc-help">
                <span>Vacío = sin globito.</span>
                <span aria-live="polite">{draft.greeting.length}/{GREETING_MAX}</span>
              </small>
            </div>

            <label className="field wc-delay">
              <span>Aparece a los</span>
              <span className="wc-affix">
                <input type="number" inputMode="numeric" min={0} max={DELAY_MAX} step={1} value={draft.greeting_delay_s}
                  disabled={!draft.greeting.trim()}
                  onChange={(e) => set({ greeting_delay_s: e.target.value === "" ? 0 : Number(e.target.value) })} />
                <span aria-hidden>segundos</span>
              </span>
            </label>

            <div className="wc-actions">
              <button className="btn primary" type="submit" disabled={!dirty || !!invalid || saving}>
                {saving ? "Guardando…" : "Guardar cambios"}
              </button>
              {dirty && !saving && (
                <button className="btn sm ghost" type="button" onClick={() => { setDraft(data.config); setHexText(data.config.color); setSaveMsg(null); }}>
                  Descartar
                </button>
              )}
              <span className={`small ${saveMsg && !saveMsg.ok ? "wc-err" : "muted"}`} role={saveMsg && !saveMsg.ok ? "alert" : "status"}>
                {saveMsg ? saveMsg.text : invalid && dirty ? invalid : dirty ? "Tenés cambios sin guardar." : ""}
              </span>
            </div>
          </form>
          <WidgetPreview config={draft} slug={data.slug} host={lastHost} />
        </div>
      </section>

      <section className="results-card wc-step" aria-labelledby="wc-s2">
        <h2 id="wc-s2"><span className="wc-n" aria-hidden>2</span> Pegá el código</h2>
        <WidgetInstallGuide snippet={data.snippet} />
      </section>

      <section className="results-card wc-step" aria-labelledby="wc-s3">
        <div className="wc-step-head">
          <h2 id="wc-s3"><span className="wc-n" aria-hidden>3</span> Verificá</h2>
          <a className="btn sm ghost" href={data.store_url} target="_blank" rel="noopener noreferrer">
            <ExternalLink size={14} strokeWidth={1.8} aria-hidden /> Abrir mi tienda
          </a>
        </div>
        <Installs installs={data.installs} refreshing={refreshing} onRefresh={() => void refresh()} />
      </section>
    </div>
  );
}

function Header() {
  return (
    <PageHeader title="Chat en tu web"
      description="Sumá tu vendedor a tu página: atiende, arma el carrito y cobra verificado, sin que tengas tienda online." />
  );
}

/** Dónde ya cargó el widget: lo reporta el propio script cuando alguien abre la página. */
function Installs({ installs, refreshing, onRefresh }: { installs: WidgetInstall[]; refreshing: boolean; onRefresh: () => void }) {
  const button = (
    <button className="btn sm" type="button" disabled={refreshing} onClick={onRefresh}>
      <RefreshCw size={14} strokeWidth={1.8} aria-hidden /> {refreshing ? "Actualizando…" : "Actualizar"}
    </button>
  );
  if (installs.length === 0) {
    return (
      <div className="wc-empty" role="status">
        <p className="muted">Todavía no lo vimos en ninguna web. Cuando alguien abra una página con el código, aparece acá.</p>
        {button}
      </div>
    );
  }
  return (
    <>
      <ul className="wc-installs" aria-busy={refreshing}>
        {installs.map((i) => (
          <li key={i.host}>
            <b>{i.host}</b>
            <span className="muted small">
              Visto por última vez <time dateTime={i.last_seen} title={new Date(i.last_seen).toLocaleString("es-AR")}>{ago(i.last_seen)}</time>
              {" · "}{i.hits.toLocaleString("es-AR")} {i.hits === 1 ? "carga" : "cargas"}
            </span>
          </li>
        ))}
      </ul>
      <div className="wc-refresh">{button}</div>
    </>
  );
}
