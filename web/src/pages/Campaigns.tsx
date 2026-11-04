import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, Megaphone, Plus } from "lucide-react";
import { CampaignComposer } from "../components/CampaignComposer";
import { Badge, EmptyState, PageHeader, Stats, type BadgeTone } from "../components/ui";
import { api, type CampaignDetail, type CampaignRecipient, type Campaigns as CampaignsData, type CampaignStatus,
  type CampaignSummary } from "../lib/api";
import { fmtAmount } from "../lib/format";

const money = (n: number) => `$${fmtAmount(Math.round(n))}`;
const when = (iso: string) => new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
const STATUS_TONE: Record<CampaignStatus, BadgeTone> = {
  draft: "neu", scheduled: "info", sending: "warn", sent: "pos", cancelled: "neu" };
const RECIPIENT_LABEL: Record<CampaignRecipient["status"], { label: string; tone: BadgeTone }> = {
  pending: { label: "Pendiente", tone: "neu" },
  sent: { label: "Enviado", tone: "pos" },
  skipped: { label: "No se envió", tone: "warn" },
  failed: { label: "Falló", tone: "neg" },
};

/** La fecha que importa según el estado: cuándo salió, cuándo sale o cuándo se armó. */
function dateOf(c: CampaignSummary): string {
  if (c.sent_at) return when(c.sent_at);
  if (c.scheduled_at && c.status === "scheduled") return `Sale ${when(c.scheduled_at)}`;
  return when(c.created_at);
}

/** Campañas: escribirles a los clientes según lo que hicieron (carritos, pagos pendientes, compras). */
export function Campaigns() {
  const [data, setData] = useState<CampaignsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.campaigns().then(setData, (e) => setError(e instanceof Error ? e.message : "No pude cargar las campañas."));
  }, []);
  useEffect(load, [load]);

  if (openId) {
    return (
      <div className="sheet">
        <CampaignView id={openId} onBack={() => { setOpenId(null); load(); }} />
      </div>
    );
  }

  return (
    <div className="sheet">
      <PageHeader title="Campañas"
        description="Escribile a tus clientes según lo que hicieron: carritos que quedaron, pagos pendientes, compras pasadas."
        actions={!creating && (
          <button className="btn primary" type="button" disabled={!data} onClick={() => setCreating(true)}>
            <Plus size={15} strokeWidth={1.8} aria-hidden /> Nueva campaña
          </button>
        )} />
      {data && !data.channel.real_sending && <p className="camp-note" role="note">{data.channel.note}</p>}
      {error && (
        <p className="state err" role="alert">
          {error}{" "}
          <button className="btn sm" type="button" onClick={load}>Reintentar</button>
        </p>
      )}
      {creating && data && (
        <CampaignComposer audiences={data.audiences} onClose={() => setCreating(false)}
          onLaunched={(c) => { setCreating(false); load(); setOpenId(c.id); }} />
      )}
      {!data ? (!error && <div className="state">Cargando…</div>) : data.campaigns.length === 0 ? (
        !creating && (
          <EmptyState icon={Megaphone} title="Todavía no mandaste ninguna campaña">
            Elegís a quién (por ejemplo, los que dejaron el carrito), escribís el mensaje y ves cómo le llega a cada uno antes de enviarlo.
            <br />
            <button className="btn sm" type="button" style={{ marginTop: 10 }} onClick={() => setCreating(true)}>
              <Plus size={14} strokeWidth={1.8} aria-hidden /> Armar la primera
            </button>
          </EmptyState>
        )
      ) : <CampaignTable campaigns={data.campaigns} onOpen={setOpenId} />}
    </div>
  );
}

function CampaignTable({ campaigns, onOpen }: { campaigns: CampaignSummary[]; onOpen: (id: string) => void }) {
  return (
    <section className="results-card camp-list" aria-labelledby="camp-list-title">
      <h2 id="camp-list-title">Tus campañas</h2>
      <table className="results-table">
        <thead>
          <tr>
            <th>Nombre</th><th className="camp-hide-sm">Audiencia</th><th>Estado</th>
            <th className="num camp-hide-sm">Enviados</th><th className="num">Compraron</th><th className="num">Facturado</th>
            <th className="camp-hide-sm">Fecha</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr key={c.id} className="camp-row" tabIndex={0} aria-label={`Abrir campaña ${c.name}`}
              onClick={() => onOpen(c.id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(c.id); } }}>
              <td><b>{c.name}</b></td>
              <td className="camp-hide-sm">{c.audience_label}</td>
              <td><Badge tone={STATUS_TONE[c.status] ?? "neu"}>{c.status_label}</Badge></td>
              <td className="num camp-hide-sm">{c.stats.sent}</td>
              <td className="num">{c.stats.converted}</td>
              <td className="num">{money(c.stats.revenue)}</td>
              <td className="camp-hide-sm">{dateOf(c)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** Detalle: números sin adornos, el mensaje y a quién le llegó. */
function CampaignView({ id, onBack }: { id: string; onBack: () => void }) {
  const [c, setC] = useState<CampaignDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.campaign(id).then((d) => { setC(d); setError(null); },
      (e) => setError(e instanceof Error ? e.message : "No pude cargar la campaña."));
  }, [id]);
  useEffect(load, [load]);

  // Mientras se está enviando, refrescar cada 5 s para ver el avance.
  useEffect(() => {
    if (c?.status !== "sending") return;
    const t = window.setInterval(load, 5000);
    return () => window.clearInterval(t);
  }, [c?.status, load]);

  async function cancel() {
    if (!c || !window.confirm(`¿Cancelar «${c.name}»? No se le va a mandar a nadie.`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.cancelCampaign(c.id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cancelar.");
    } finally {
      setBusy(false);
    }
  }

  const back = (
    <button className="btn sm ghost camp-back" type="button" onClick={onBack}>
      <ArrowLeft size={15} strokeWidth={1.8} aria-hidden /> Campañas
    </button>
  );
  if (!c) {
    return (
      <>
        {back}
        {error ? <p className="state err" role="alert">{error}</p> : <div className="state">Cargando…</div>}
      </>
    );
  }

  const s = c.stats;
  const subtitle = [c.audience_label,
    c.status === "scheduled" && c.scheduled_at ? `sale el ${when(c.scheduled_at)}` : c.sent_at ? `enviada el ${when(c.sent_at)}` : null,
  ].filter(Boolean).join(" · ");
  return (
    <>
      {back}
      <PageHeader title={c.name}
        description={<span className="camp-sub"><Badge tone={STATUS_TONE[c.status] ?? "neu"}>{c.status_label}</Badge> {subtitle}</span>}
        actions={(c.status === "draft" || c.status === "scheduled" || c.status === "sending") && (
          <button className="btn" type="button" disabled={busy} onClick={() => void cancel()}>
            {busy ? "Cancelando…" : "Cancelar campaña"}
          </button>
        )} />
      {error && <p className="state err" role="alert">{error}</p>}
      <Stats label="Resultados de la campaña" items={[
        { label: "Destinatarios", value: s.recipients,
          hint: s.skipped || s.failed ? [s.skipped && `${s.skipped} sin enviar`, s.failed && `${s.failed} fallaron`].filter(Boolean).join(" · ") : undefined },
        { label: "Enviados", value: s.sent },
        { label: "Compraron", value: s.converted },
        { label: "Facturado", value: money(s.revenue) },
      ]} />
      <section className="results-card camp-message" aria-labelledby="camp-msg-title">
        <h2 id="camp-msg-title">Mensaje</h2>
        <div className="bubble bot">{c.message}</div>
      </section>
      <section className="results-card" aria-labelledby="camp-rec-title">
        <h2 id="camp-rec-title">Destinatarios</h2>
        {c.recipients.length === 0 ? (
          <p className="muted small">
            {c.status === "draft" || c.status === "scheduled" ? "La lista se arma cuando sale la campaña." : "No hubo destinatarios."}
          </p>
        ) : (
          <table className="results-table">
            <thead><tr><th>Cliente</th><th className="camp-hide-sm">Detalle</th><th>Estado</th><th>Compró</th></tr></thead>
            <tbody>
              {c.recipients.map((r, i) => {
                const st = RECIPIENT_LABEL[r.status] ?? { label: r.status, tone: "neu" as const };
                return (
                  <tr key={`${r.name}-${i}`}>
                    <td>
                      {r.name}
                      {r.message && (
                        <details className="camp-rec-msg">
                          <summary className="small">Ver mensaje</summary>
                          <div className="bubble bot">{r.message}</div>
                        </details>
                      )}
                    </td>
                    <td className="camp-hide-sm muted">{r.detail}</td>
                    <td>
                      <Badge tone={st.tone}>{st.label}</Badge>
                      {r.reason && <div className="muted small">{r.reason}</div>}
                    </td>
                    <td>{r.converted
                      ? <><Check size={16} strokeWidth={2} aria-hidden className="camp-yes" /><span className="sr-only">Sí</span></>
                      : <span className="muted" aria-label="No">—</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
