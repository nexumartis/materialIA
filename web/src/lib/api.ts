// Cliente de la API FastAPI de Presupuesto Vivo.
// La base se toma de VITE_API_BASE (ver .env.example); nunca se hardcodea el tenant.
// - Panel (/app/*): va con `Authorization: Bearer <jwt>`; el backend deriva el negocio
//   de la sesión. Ninguna llamada /app manda empresa.
// - Demo sin cuenta (/sandbox/chat): la empresa A/B va como query param y el backend
//   la resuelve contra su allowlist.

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ||
  "http://127.0.0.1:8077";

export type Company = "A" | "B";

export type Stage =
  | "nueva"
  | "datos_incompletos"
  | "para_cotizar"
  | "cotizada"
  | "seguimiento"
  | "cerrada";

export interface Requirements {
  category?: string;
  tipo?: string;
  color?: string;
  material?: string;
  ancho_mm?: number;
  alto_mm?: number;
  localidad?: string;
  customer_name?: string;
  product_id?: string;
  quantity?: number;
  [k: string]: unknown;
}

export interface Opportunity {
  id: string;
  created_at: string;
  stage: Stage;
  estimated_amount: number | null;
  next_action_at: string | null;
  requirements: Requirements;
}

export interface Health {
  status: string;
  db: { reachable: boolean; detail?: string };
  app_env?: string;
  llm: { mode: "mock" | "live"; model?: string };
}

export interface OpportunityPatch {
  stage?: Stage;
  estimated_amount?: number;
  next_action_at?: string;
}

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  collected_requirements: Requirements;
  missing_fields: string[];
  requires_human: boolean;
  mode: string;
  opportunity_id?: string | null;
}

export interface Activity {
  kind: string;
  detail: string;
  created_at: string;
}

export interface Me {
  user_id: string;
  tenant_id: string;
  business_name: string;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

let getToken: () => string | null = () => null;
let onUnauthorized: () => void = () => {};

/** Lo registra la sesión: de dónde sale el token y qué hacer ante un 401. */
export function setAuth(token: () => string | null, unauthorized: () => void): void {
  getToken = token;
  onUnauthorized = unauthorized;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "No se pudo conectar con la API.");
  }
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`);
  return (await res.json()) as T;
}

/** Llamada al panel autenticado. Sin token o con 401 => se cierra la sesión. */
async function authed<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  if (!token) {
    onUnauthorized();
    throw new ApiError(401, "Sesión no iniciada.");
  }
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${token}`);
  try {
    return await request<T>(path, { ...init, headers });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) onUnauthorized();
    throw e;
  }
}

export const api = {
  health: () => request<Health>("/health"),

  me: () => authed<Me>("/app/me"),

  opportunities: () => authed<Opportunity[]>("/app/opportunities"),

  patchOpportunity: (id: string, body: OpportunityPatch) =>
    authed<Opportunity>(`/app/opportunities/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),

  chat: (company: Company, message: string, conversationId: string | null) =>
    request<ChatResponse>(`/sandbox/chat?company=${company}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    }),

  activity: (id: string) => authed<Activity[]>(`/app/opportunities/${id}/activity`),
};

export { ApiError };
