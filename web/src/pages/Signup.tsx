import { useState } from "react";
import { supabase } from "../lib/supabase";
import { AuthForm, authErrorMessage, type AuthField } from "./AuthForm";

const EMAIL: AuthField = { name: "email", label: "Email", type: "email", autoComplete: "email" };
const PASSWORD: AuthField = {
  name: "password",
  label: "Contraseña",
  type: "password",
  autoComplete: "new-password",
  minLength: 8,
  hint: "Mínimo 8 caracteres.",
};

/** Registro de un negocio nuevo o, si te invitaron, de un integrante del equipo (sin negocio propio:
 *  la base lo suma al negocio que invitó ese email). */
export function Signup() {
  const [invited, setInvited] = useState(() => window.location.hash === "#/signup/equipo");
  const home = invited ? "#/conversaciones" : "#/asistente";

  return (
    <AuthForm
      key={invited ? "equipo" : "negocio"}
      title={invited ? "Sumate a tu equipo" : "Registrá tu negocio"}
      lead={invited
        ? "Usá el mismo email con el que te invitó el dueño. Al crear la cuenta entrás directo a su negocio."
        : "Creás tu cuenta de propietario y el espacio de tu negocio. Sus datos quedan separados de los de cualquier otra empresa."}
      submitLabel={invited ? "Crear cuenta y entrar" : "Crear cuenta"}
      fields={invited ? [EMAIL, PASSWORD]
        : [{ name: "business_name", label: "Nombre del negocio", type: "text", autoComplete: "organization" }, EMAIL, PASSWORD]}
      onSubmit={async ({ business_name, email, password }) => {
        const { data, error } = await supabase!.auth.signUp({
          email,
          password,
          options: {
            data: invited ? {} : { business_name: (business_name ?? "").trim() },
            // El link del correo de confirmación vuelve a este panel (debe estar en las
            // Redirect URLs permitidas del proyecto; si no, Supabase usa el Site URL).
            emailRedirectTo: `${window.location.origin}/${home}`,
          },
        });
        if (error) throw new Error(authErrorMessage(error.message));
        if (!data.session) {
          // Proyecto con confirmación de email: no hay sesión hasta confirmar.
          return "Te enviamos un correo para confirmar la cuenta. Después iniciá sesión.";
        }
        // Un negocio nuevo arranca por el asistente; un integrante, por la bandeja.
        window.location.hash = home;
      }}
      footer={
        <>
          {invited ? (
            <>¿Querés registrar tu propio negocio? <button type="button" className="linkish" onClick={() => setInvited(false)}>Registrar negocio</button></>
          ) : (
            <>¿Te invitaron a un equipo? <button type="button" className="linkish" onClick={() => setInvited(true)}>Sumarme al equipo</button></>
          )}
          <br />
          ¿Ya tenés cuenta? <a href="#/login">Iniciá sesión</a>
        </>
      }
    />
  );
}
