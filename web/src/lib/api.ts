// Cliente de la API FastAPI de Presupuesto Vivo.
// La base se toma de VITE_API_BASE (ver .env.example); nunca se hardcodea el tenant.
// - Panel (/app/*): va con `Authorization: Bearer <jwt>`; el backend deriva el negocio
//   de la sesión. Ninguna llamada /app manda empresa.
// - Agente de ventas demo sin cuenta (/sandbox/sales/*): empresa demo C, resuelta por el
//   backend contra su allowlist.

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ||
  "http://127.0.0.1:8077";

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
  payments?: { provider: string };
}

export interface OpportunityPatch {
  stage?: Stage;
  estimated_amount?: number;
  next_action_at?: string;
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


  activity: (id: string) => authed<Activity[]>(`/app/opportunities/${id}/activity`),

  // Agente de ventas (empresa demo C, sin cuenta).
  salesChat: (message: string, conversationId: string | null) =>
    request<SalesResponse>(`/sandbox/sales/chat?company=C`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    }),

  salesConversation: (conversationId: string) =>
    request<SalesConversation>(`/sandbox/sales/${conversationId}?company=C`),
};

export interface OrderLine {
  item_id: string;
  sku: string;
  name: string;
  qty: number;
  unit_price: number;
  line_total: number;
}

export interface Order {
  id: string;
  number: number;
  status: string;
  status_label: string;
  total: number;
  currency: string;
  items: OrderLine[];
  reserved_until: string | null;
  attention_reason: string | null;
  payment: { provider: string; checkout_url: string | null; status: string } | null;
}

export interface QuickReply {
  label: string;
  message: string;
}

export interface ProductCard {
  n: number;
  name: string;
  brand: string | null;
  image_url: string | null;
  price: number | null;
  available: number;
  pricing_mode: string;
  description: string;
  specs: Record<string, unknown>;
  action: QuickReply | null;
}

/** Contenido interactivo de un mensaje del agente (tarjetas, botones, pago). */
export interface MessageUI {
  products?: ProductCard[];
  quick_replies?: QuickReply[];
  payment?: { url: string; provider: string };
}

export interface SalesResponse {
  reply: string;
  conversation_id: string;
  mode: string;
  requires_human: boolean;
  cart: Order | null;
  orders: Order[];
  payment: { provider: string; checkout_url: string } | null;
  trace: { name: string; summary: string }[];
  ui: MessageUI;
}

export interface SalesConversation {
  messages: { role: "user" | "assistant"; content: string; ui: MessageUI | null }[];
  cart: Order | null;
  orders: Order[];
}

export { ApiError };
