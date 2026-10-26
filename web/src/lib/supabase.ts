// Cliente de Supabase Auth (sólo identidad: registro, login, sesión).
// La URL y la anon key son públicas por diseño; igual viven en .env (ver .env.example).
// Los datos NO se leen con este cliente: el panel los pide a la API FastAPI con el JWT.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null;
