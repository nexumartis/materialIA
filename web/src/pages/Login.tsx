import { supabase } from "../lib/supabase";
import { AuthForm, authErrorMessage } from "./AuthForm";

export function Login() {
  return (
    <AuthForm
      title="Iniciar sesión"
      lead="Entrá al panel de tu negocio."
      submitLabel="Entrar"
      fields={[
        { name: "email", label: "Email", type: "email", autoComplete: "email" },
        { name: "password", label: "Contraseña", type: "password", autoComplete: "current-password" },
      ]}
      onSubmit={async ({ email, password }) => {
        const { error } = await supabase!.auth.signInWithPassword({ email, password });
        if (error) throw new Error(authErrorMessage(error.message));
        window.location.hash = "#/oportunidades";
      }}
      footer={
        <>
          ¿No tenés cuenta? <a href="#/signup">Registrá tu negocio</a>
        </>
      }
    />
  );
}
