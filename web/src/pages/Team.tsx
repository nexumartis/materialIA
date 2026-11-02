import { useCallback, useEffect, useState } from "react";
import { UserPlus, Users } from "lucide-react";
import { Badge, EmptyState, PageHeader } from "../components/ui";
import { api, type Team } from "../lib/api";

const ROLE = { owner: "Dueño", staff: "Empleado" } as const;

/** Equipo del negocio: el dueño invita por email y quita accesos. No se envían emails. */
export function TeamPage() {
  const [team, setTeam] = useState<Team | null>(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (await run(() => api.invite(email.trim()))) setEmail("");
  }

  return (
    <div className="sheet">
      <PageHeader title="Equipo"
        description="Sumá a quienes atienden: ven la bandeja, los pedidos y las oportunidades. La plata, el catálogo y la configuración del agente siguen siendo sólo tuyos." />

      <form className="team-invite" onSubmit={(e) => void invite(e)}>
        <label htmlFor="invite-email">Invitar por email</label>
        <div className="row">
          <input id="invite-email" type="email" required autoComplete="off" placeholder="nombre@minegocio.com"
            value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="btn primary" type="submit" disabled={busy || !email.trim()}>
            <UserPlus size={15} strokeWidth={1.8} aria-hidden /> Invitar
          </button>
        </div>
        <p className="muted small">
          No mandamos emails: avisale que se registre en Presupuesto Vivo con ese email y, al confirmarlo, entra a tu negocio.
        </p>
      </form>
      {error && <p className="state err" role="alert">{error}</p>}

      {!team ? (
        !error && <div className="state">Cargando…</div>
      ) : (
        <>
          <ul className="team-list" aria-label="Integrantes">
            {team.members.map((m) => (
              <li key={m.user_id}>
                <span className="who">{m.email ?? "—"}</span>
                <Badge tone={m.role === "owner" ? "neu" : "info"}>{ROLE[m.role]}</Badge>
                {m.role === "staff" && (
                  <button className="btn sm" type="button" disabled={busy}
                    onClick={() => window.confirm(`¿Quitar el acceso de ${m.email ?? "esta persona"}?`)
                      && void run(() => api.removeMember(m.user_id))}>
                    Quitar acceso
                  </button>
                )}
              </li>
            ))}
          </ul>
          {team.invites.length > 0 ? (
            <>
              <h2 className="team-sub">Invitaciones pendientes</h2>
              <ul className="team-list" aria-label="Invitaciones pendientes">
                {team.invites.map((i) => (
                  <li key={i.email}>
                    <span className="who">{i.email}</span>
                    <Badge tone="warn">Sin registrarse</Badge>
                    <button className="btn sm" type="button" disabled={busy}
                      onClick={() => void run(() => api.cancelInvite(i.email))}>Cancelar</button>
                  </li>
                ))}
              </ul>
            </>
          ) : team.members.length === 1 && (
            <EmptyState icon={Users} title="Todavía trabajás solo">
              Invitá a quien te ayuda a atender y va a poder tomar conversaciones y dejar notas internas.
            </EmptyState>
          )}
        </>
      )}
    </div>
  );
}
