import { supabase } from "../lib/supabase";
import { AuthForm, authErrorMessage } from "./AuthForm";

export function Signup() {
  return (
    <AuthForm
      title="Registrá tu negocio"
      lead="Creás tu cuenta de propietario y el espacio de tu negocio. Sus datos quedan separados de los de cualquier otra empresa."
      submitLabel="Crear cuenta"
      fields={[
        { name: "business_name", label: "Nombre del negocio", type: "text", autoComplete: "organization" },
        { name: "email", label: "Email", type: "email", autoComplete: "email" },
        {
          name: "password",
          label: "Contraseña",
          type: "password",
          autoComplete: "new-password",
          minLength: 8,
          hint: "Mínimo 8 caracteres.",
        },
      ]}
      onSubmit={async ({ business_name, email, password }) => {
        const { data, error } = await supabase!.auth.signUp({
          email,
          password,
          options: {
            data: { business_name: business_name.trim() },
            // El link del correo de confirmación vuelve a este panel (debe estar en las
            // Redirect URLs permitidas del proyecto; si no, Supabase usa el Site URL).
            emailRedirectTo: `${window.location.origin}/#/asistente`,
          },
        });
        if (error) throw new Error(authErrorMessage(error.message));
        if (!data.session) {
          // Proyecto con confirmación de email: no hay sesión hasta confirmar.
          return "Te enviamos un correo para confirmar la cuenta. Después iniciá sesión.";
        }
        // Un negocio nuevo arranca por el asistente para crear su agente.
        window.location.hash = "#/asistente";
      }}
      footer={
        <>
          ¿Ya tenés cuenta? <a href="#/login">Iniciá sesión</a>
        </>
      }
    />
  );
}
