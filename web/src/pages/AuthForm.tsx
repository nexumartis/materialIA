// Formulario compartido de login/registro (Supabase Auth, email + contraseña).
import { useState, type FormEvent, type ReactNode } from "react";

export interface AuthField {
  name: string;
  label: string;
  type: string;
  autoComplete: string;
  minLength?: number;
  hint?: string;
}

export function AuthForm({
  title,
  lead,
  fields,
  submitLabel,
  onSubmit,
  footer,
}: {
  title: string;
  lead: string;
  fields: AuthField[];
  submitLabel: string;
  onSubmit: (values: Record<string, string>) => Promise<ReactNode | void>;
  footer: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<ReactNode | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const msg = await onSubmit(values);
      if (msg) setNotice(msg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar la operación.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sheet auth-sheet">
      <form className="auth" onSubmit={submit} noValidate={false}>
        <h1>{title}</h1>
        <p className="auth-lead">{lead}</p>
        {fields.map((f) => (
          <label className="field" key={f.name}>
            <span>{f.label}</span>
            <input
              name={f.name}
              type={f.type}
              autoComplete={f.autoComplete}
              minLength={f.minLength}
              required
            />
            {f.hint && <small>{f.hint}</small>}
          </label>
        ))}
        {error && (
          <p className="auth-msg err" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="auth-msg ok" role="status">
            {notice}
          </p>
        )}
        <button className="btn primary auth-submit" type="submit" disabled={busy}>
          {busy ? "Un momento…" : submitLabel}
        </button>
        <p className="auth-foot">{footer}</p>
      </form>
    </div>
  );
}

/** Traduce los errores más comunes de Supabase Auth; el resto, genérico (sin filtrar detalles). */
export function authErrorMessage(message: string): string {
  const m = message.toLowerCase();
  if (m.includes("invalid login credentials")) return "Email o contraseña incorrectos.";
  if (m.includes("email not confirmed")) return "Todavía no confirmaste tu email. Revisá tu correo.";
  if (m.includes("already registered")) return "Ya existe una cuenta con ese email. Iniciá sesión.";
  if (m.includes("password")) return "La contraseña no cumple los requisitos (mínimo 8 caracteres).";
  if (m.includes("fetch") || m.includes("network")) return "No se pudo conectar con el servicio de cuentas.";
  return "No se pudo completar la operación. Probá de nuevo.";
}
