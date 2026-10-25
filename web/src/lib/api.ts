// Cliente de la API FastAPI de Presupuesto Vivo.
// La base se toma de VITE_API_BASE (ver .env.example); nunca se hardcodea el tenant:
// la empresa va como query param y el backend resuelve el tenant real.

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

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
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

export const api = {
  health: () => request<Health>("/health"),

  opportunities: (company: Company) =>
    request<Opportunity[]>(`/sandbox/opportunities?company=${company}`),

  patchOpportunity: (company: Company, id: string, body: OpportunityPatch) =>
    request<unknown>(`/sandbox/opportunities/${id}?company=${company}`, {
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
};

export { ApiError };
