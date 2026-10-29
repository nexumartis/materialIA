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

async function request<T>(path: string, init?: RequestInit, as: "json" | "blob" = "json"): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "No se pudo conectar con la API.");
  }
  if (!res.ok) {
    // El backend explica el error en `detail` (p. ej. "Ese link ya lo usa otro negocio").
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return (as === "blob" ? await res.blob() : await res.json()) as T;
}

/** Llamada al panel autenticado. Sin token o con 401 => se cierra la sesión. */
async function authed<T>(path: string, init: RequestInit = {}, as: "json" | "blob" = "json"): Promise<T> {
  const token = getToken();
  if (!token) {
    onUnauthorized();
    throw new ApiError(401, "Sesión no iniciada.");
  }
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${token}`);
  try {
    return await request<T>(path, { ...init, headers }, as);
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
  salesChat: (message: string, ref: ConversationRef | null) =>
    request<SalesResponse>(`/sandbox/sales/chat?company=C`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, conversation_id: ref?.id ?? null }),
    }),

  salesConversation: (ref: ConversationRef) =>
    request<SalesConversation>(`/sandbox/sales/${encodeURIComponent(ref.id)}?company=C`),

  // Panel: el negocio arma su agente.
  agentTemplates: () => authed<{ key: string; label: string }[]>("/app/agent-templates"),
  agentProfile: () => authed<AgentProfile>("/app/agent-profile"),
  saveAgentProfile: (body: Partial<AgentProfile> & { apply_template?: boolean; require_evals?: boolean }) =>
    authed<AgentProfile>("/app/agent-profile", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  catalog: () => authed<CatalogItem[]>("/app/catalog"),
  updateProduct: (id: string, body: { price?: number; stock?: number; active?: boolean }) =>
    authed<CatalogItem>(`/app/catalog/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  importCatalog: (csv: string) =>
    authed<ImportResult>("/app/catalog/import", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ csv }),
    }),
  orders: () => authed<Order[]>("/app/orders"),
  // Comprobantes: el dueño revisa los archivos y acredita sólo lo que cotejó en su banco.
  paymentDocuments: (month: string) =>
    authed<PaymentDocument[]>(`/app/payment-documents?month=${encodeURIComponent(month)}`),
  documentOriginal: (id: string) => authed<Blob>(`/app/payment-documents/${id}/original`, {}, "blob"),
  rejectDocument: (id: string) => authed<{ rejected: boolean }>(`/app/payment-documents/${id}/reject`, { method: "POST" }),
  confirmTransfer: (orderId: string, body: TransferConfirm) =>
    authed<{ outcome: string; order: Order }>(`/app/orders/${orderId}/confirm-transfer`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  paymentRegister: (month: string) =>
    authed<Blob>(`/app/payments/register.csv?month=${encodeURIComponent(month)}`, {}, "blob"),
  orderReceipt: (orderId: string) => authed<Blob>(`/app/orders/${orderId}/receipt.pdf`, {}, "blob"),
  advanceOrder: (id: string, status: string) =>
    authed<Order>(`/app/orders/${id}/status?status=${status}`, { method: "POST" }),

  // Tienda pública de cada negocio (sin cuenta). El token del comprador va en un header,
  // nunca en la URL.
  store: (slug: string) => request<StoreInfo>(`/public/${encodeURIComponent(slug)}`),
  storeChat: (slug: string, message: string, ref: ConversationRef | null) =>
    request<SalesResponse>(`/public/${encodeURIComponent(slug)}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json", ...buyerHeader(ref) },
      body: JSON.stringify({ message, conversation_id: ref?.id ?? null }),
    }),
  forgetMe: (slug: string) =>
    request<{ forgotten: boolean }>(`/public/${encodeURIComponent(slug)}/me`, {
      method: "DELETE",
      headers: buyerHeader(null),
    }),

  // Arquitectura del agente: versiones, herramientas, conocimiento y pruebas.
  agentTools: () => authed<{ key: string; label: string }[]>("/app/agent-tools"),
  profileVersions: () => authed<ProfileVersion[]>("/app/agent-profile/versions"),
  restoreVersion: (version: number) =>
    authed<AgentProfile>(`/app/agent-profile/versions/${version}/restore`, { method: "POST" }),
  knowledge: () => authed<KnowledgeDoc[]>("/app/knowledge"),
  addKnowledge: (title: string, text: string) =>
    authed<KnowledgeDoc>("/app/knowledge", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title, text }),
    }),
  deleteKnowledge: (id: string) => authed<{ deleted: boolean }>(`/app/knowledge/${id}`, { method: "DELETE" }),
  evalCases: () => authed<EvalCase[]>("/app/agent-evals"),
  addEvalCase: (c: Omit<EvalCase, "id">) =>
    authed<EvalCase>("/app/agent-evals", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(c),
    }),
  deleteEvalCase: (id: string) => authed<{ deleted: boolean }>(`/app/agent-evals/${id}`, { method: "DELETE" }),
  runEvals: (profile?: Partial<AgentProfile>) =>
    authed<EvalRun>("/app/agent-evals/run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(profile ? { profile } : {}),
    }),

  /** Comprobante de pago del comprador: el archivo va crudo en el cuerpo, el token en el header. */
  uploadDocument: (slug: string, ref: ConversationRef, orderId: string, file: File) =>
    request<{ document: BuyerDocument; note: string }>(
      `/public/${encodeURIComponent(slug)}/conversations/${encodeURIComponent(ref.id)}/orders/${orderId}/documents`,
      { method: "POST", headers: { "content-type": file.type || "application/octet-stream", ...buyerHeader(ref) }, body: file },
    ),
  storeReceipt: (slug: string, ref: ConversationRef, receiptId: string) =>
    request<Blob>(
      `/public/${encodeURIComponent(slug)}/conversations/${encodeURIComponent(ref.id)}/receipts/${receiptId}/pdf`,
      { headers: buyerHeader(ref) },
      "blob",
    ),

  storeConversation: (slug: string, ref: ConversationRef) =>
    request<SalesConversation>(
      `/public/${encodeURIComponent(slug)}/conversations/${encodeURIComponent(ref.id)}`,
      { headers: buyerHeader(ref) },
    ),
};

/** Referencia del comprador a su conversación. En la tienda pública lleva el token que emitió el
 *  servidor al crearla: sin él, la UUID sola no abre la conversación. */
export interface ConversationRef {
  id: string;
  token: string | null;
}

/** Clave aleatoria de este navegador para que la tienda recuerde preferencias del comprador.
 * El servidor guarda sólo un hash por negocio; "Olvidarme" la borra. */
const BUYER_KEY = "pv.comprador.clave";

export function buyerKey(): string | null {
  try {
    let key = localStorage.getItem(BUYER_KEY);
    if (!key) {
      const bytes = crypto.getRandomValues(new Uint8Array(24));
      key = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
      localStorage.setItem(BUYER_KEY, key);
    }
    return key;
  } catch {
    return null; // sin almacenamiento (modo privado): la tienda funciona sin memoria
  }
}

export function resetBuyerKey(): void {
  try {
    localStorage.removeItem(BUYER_KEY);
  } catch {
    /* sin almacenamiento */
  }
}

function buyerHeader(ref: ConversationRef | null): Record<string, string> {
  const key = buyerKey();
  return { ...(ref?.token ? { "x-conversation-token": ref.token } : {}), ...(key ? { "x-buyer-key": key } : {}) };
}

export interface AgentProfile {
  business_type: string;
  public_slug: string;
  seller_name: string;
  tone: "cercano" | "profesional" | "formal";
  greeting: string;
  faq: { q: string; a: string }[];
  rules: string[];
  shipping: string;
  hours: string;
  payment_methods: string;
  policies: Policies;
  disabled_tools: string[];
  version: number;
  updated_at: string;
}

/** Reglas que hace cumplir el código (no el modelo). */
export interface Policies {
  min_order_total?: number;
  delivery_zones?: string[];
  human_only_categories?: string[];
}

export interface ProfileVersion {
  version: number;
  created_at: string;
  seller_name: string | null;
  tone: string | null;
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  chars: number;
  chunks: number;
  created_at: string;
}

export interface EvalCase {
  id: string;
  message: string;
  expect_contains: string[];
  expect_not_contains: string[];
}

export interface EvalRun {
  passed: number;
  total: number;
  results: { id: string | null; message: string; reply: string; passed: boolean; failures: string[] }[];
}

export interface CatalogItem {
  id: string;
  sku: string;
  name: string;
  brand: string | null;
  category: string;
  pricing_mode: string;
  price: number | null;
  available: number;
  on_hand: number;
  reserved: number;
  active: boolean;
  image_url: string | null;
  specs: Record<string, unknown>;
}

export interface ImportResult {
  created: number;
  updated: number;
  errors: { fila: number; sku?: string; error: string }[];
}

export interface StoreInfo {
  name: string;
  seller_name: string | null;
  greeting: string | null;
  payments: string;
}

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
  /** Constancia de compra emitida (sólo pedidos pagados). */
  receipt_id: string | null;
}

/** Campo leído de un comprobante: sugerido o, si es dudoso, sólo candidatos. */
export interface DocField {
  value: string | null;
  candidates: string[];
}

/** Lo que el comprador ve de su comprobante (nunca el texto completo del archivo). */
export interface BuyerDocument {
  id: string;
  order_number: number;
  status: "received" | "processing" | "read" | "unreadable";
  decision: "linked" | "rejected" | null;
  fields: Record<string, DocField>;
  needs_review: boolean | null;
  received_at: string;
}

export interface PaymentDocument {
  id: string;
  order_id: string;
  order_number: number;
  total: number;
  currency: string;
  order_status: string;
  mime: string;
  size: number;
  pages: number | null;
  status: BuyerDocument["status"];
  error: string | null;
  fields: Record<string, DocField & { score: number | null }> | null;
  needs_review: boolean | null;
  decision: BuyerDocument["decision"];
  decided_at: string | null;
  payment_id: string | null;
  received_at: string;
}

export interface TransferConfirm {
  reference: string;
  amount: number;
  currency: string;
  document_ids: string[];
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
  /** Mensaje de pago confirmado con su constancia. */
  type?: string;
  receipt_id?: string;
}

export interface SalesResponse {
  reply: string;
  conversation_id: string;
  /** Sólo tienda pública y sólo al crear la conversación. */
  conversation_token?: string | null;
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
  /** Sólo tienda pública. */
  documents?: BuyerDocument[];
}

export { ApiError };
