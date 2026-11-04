import { useCallback, useEffect, useState } from "react";
import { UserPlus } from "lucide-react";
import { Badge, PageHeader } from "../components/ui";
import { api, type QuickReply, type Team, type TeamRole } from "../lib/api";
import { useSession } from "../lib/session";

const ROLE = { owner: "Dueño", staff: "Empleado", driver: "Reparto" } as const;
const ROLE_CHOICES: { id: TeamRole; label: string; hint: string }[] = [
  { id: "staff", label: "Atiende el panel", hint: "Ve la bandeja, los pedidos y las oportunidades." },
  { id: "driver", label: "Reparto e instalación", hint: "Sólo ve sus entregas del día en el celular, no el panel." },
];

/** Equipo del negocio: el dueño invita por email y quita accesos. No se envían emails. */
export function TeamPage() {
  const { me } = useSession();
  // Sin reparto propio no hay a quién invitar como repartidor.
  const choices = ROLE_CHOICES.filter((c) => c.id !== "driver" || me?.modules?.reparto !== false);
  const [team, setTeam] = useState<Team | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<TeamRole>("staff");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    api.team().then(setTeam, (e) => setError(e instanceof Error ? e.message : "No pude cargar el equipo."));
  }, []);
  useEffect(load, [load]);

  async function run(action: () => Promise<Team>) {
    setBusy(true);
    setError(null);
    try {
      setTeam(await action());
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    if (await run(() => api.invite(email.trim(), role))) setEmail("");
  }

  return (
    <div className="sheet">
      <PageHeader title="Equipo"
        description="Sumá a quienes atienden: ven la bandeja, los pedidos y las oportunidades. La plata, el catálogo y la configuración del agente siguen siendo sólo tuyos." />

      <div className="team-grid">
        <section className="panel" aria-labelledby="people-title">
          <header className="panel-head">
            <h2 id="people-title">Personas {team && <span className="muted">{team.members.length}</span>}</h2>
          </header>
          <fieldset className="role-choice">
            <legend className="sr">Qué va a hacer</legend>
            {choices.map((c) => (
              <label key={c.id} className={role === c.id ? "on" : ""}>
                <input type="radio" name="invite-role" value={c.id} checked={role === c.id} onChange={() => setRole(c.id)} />
                <span><b>{c.label}</b><small className="muted">{c.hint}</small></span>
              </label>
            ))}
          </fieldset>
          <form className="inline-form" onSubmit={(e) => void invite(e)}>
            <label className="sr" htmlFor="invite-email">Email de la persona a invitar</label>
            <input id="invite-email" type="email" required autoComplete="off" placeholder={role === "driver" ? "Email de quien reparte" : "Email de quien te ayuda a atender"}
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <button className="btn primary" type="submit" disabled={busy || !email.trim()}>
              <UserPlus size={15} strokeWidth={1.8} aria-hidden /> Invitar
            </button>
          </form>
          <p className="muted small panel-note">
            No mandamos emails: pasale el{" "}
            <a className="link" href="#/signup/equipo" onClick={(e) => { e.preventDefault(); void navigator.clipboard?.writeText(`${window.location.origin}/#/signup/equipo`); setCopied(true); }}>
              {copied ? "link copiado" : "link para sumarse"}
            </a>{" "}y que se registre con ese email.
          </p>
          {error && <p className="state err" role="alert">{error}</p>}
          {!team ? (!error && <div className="state">Cargando…</div>) : (
            <ul className="people" aria-label="Integrantes">
              {team.members.map((m) => (
                <li key={m.user_id}>
                  <Avatar text={m.email ?? "?"} />
                  <span className="person">
                    <b>{m.email ?? "—"}</b>
                    <small className="muted">{ROLE[m.role]} · desde {since(m.since)}</small>
                  </span>
                  {m.role !== "owner" ? (
                    <button className="btn sm ghost" type="button" disabled={busy}
                      onClick={() => window.confirm(`¿Quitar el acceso de ${m.email ?? "esta persona"}?`)
                        && void run(() => api.removeMember(m.user_id))}>
                      Quitar acceso
                    </button>
                  ) : <Badge tone="neu">Dueño</Badge>}
                </li>
              ))}
              {team.invites.map((i) => (
                <li key={i.email} className="pending">
                  <Avatar text={i.email} pending />
                  <span className="person">
                    <b>{i.email}</b>
                    <small className="muted">{ROLE[i.role] ?? "Empleado"} · invitado, todavía no se registró</small>
                  </span>
                  <button className="btn sm ghost" type="button" disabled={busy}
                    onClick={() => void run(() => api.cancelInvite(i.email))}>Cancelar</button>
                </li>
              ))}
              {team.members.length === 1 && team.invites.length === 0 && (
                <li className="people-empty muted small">Todavía trabajás solo. Invitá a quien te ayuda a atender: va a poder tomar conversaciones y dejar notas internas.</li>
              )}
            </ul>
          )}
        </section>
        <QuickReplies />
      </div>
    </div>
  );
}

const since = (iso: string) => new Date(iso).toLocaleDateString("es-AR", { day: "numeric", month: "short", year: "numeric" });

/** Inicial con un tono pálido propio y estable por persona (identidad, no dato). */
function Avatar({ text, pending = false }: { text: string; pending?: boolean }) {
  let h = 0;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return (
    <span className={`avatar${pending ? " pending" : ""}`} aria-hidden
      style={pending ? undefined : { background: `hsl(${h} 70% 93%)`, color: `hsl(${h} 45% 32%)` }}>
      {text.trim().charAt(0).toUpperCase()}
    </span>
  );
}

/** Respuestas rápidas que usa el equipo en la bandeja (sin precios: salen del catálogo). */
function QuickReplies() {
  const [items, setItems] = useState<QuickReply[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { api.quickReplies().then(setItems, () => setItems([])); }, []);
  useEffect(load, [load]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createQuickReply(title.trim(), body.trim());
      setTitle("");
      setBody("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pude guardarla.");
    }
  }
  return (
    <section className="panel" aria-labelledby="qr-title">
      <header className="panel-head"><h2 id="qr-title">Respuestas rápidas {items.length > 0 && <span className="muted">{items.length}</span>}</h2></header>
      <p className="muted small panel-note">Tu equipo las inserta con un clic en la bandeja. Sin precios: el precio sale del catálogo al momento.</p>
      {items.length > 0 && (
        <ul className="people">
          {items.map((q) => (
            <li key={q.id}>
              <span className="person"><b>{q.title}</b><small className="muted">{q.body}</small></span>
              <button className="btn sm ghost" type="button"
                onClick={() => void api.deleteQuickReply(q.id).then(load, (err) => setError(err instanceof Error ? err.message : "No pude quitarla."))}>
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="qr-form" onSubmit={(e) => void add(e)}>
        <input aria-label="Título" placeholder="Título (ej.: Horarios)" maxLength={60} value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea aria-label="Texto" rows={2} maxLength={1000} placeholder="Abrimos de lunes a viernes de 8 a 18 y sábados de 9 a 13."
          value={body} onChange={(e) => setBody(e.target.value)} />
        <div><button className="btn sm" type="submit" disabled={!title.trim() || !body.trim()}>Agregar</button></div>
      </form>
      {error && <p className="state err" role="alert">{error}</p>}
    </section>
  );
}
