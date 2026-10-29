// Aceptación en navegador de comprobantes y constancia (T4): el comprador adjunta su comprobante,
// el dueño lo revisa y confirma la transferencia, y el comprador baja su constancia.
// Opera SÓLO sobre servicios locales (loopback) con una base de prueba y el seed sintético C.
// Instrucciones: e2e/README.md.  Uso: E2E_OWNER_EMAIL=… E2E_OWNER_PASSWORD=… npm run e2e:comprobantes
import { chromium } from "playwright-core";

const API = process.env.E2E_API || "http://127.0.0.1:8077";
const WEB = process.env.E2E_WEB || "http://127.0.0.1:4173";
const C = "sanitarios-demo-c"; // tienda pública del seed (datos sintéticos)
const EMAIL = process.env.E2E_OWNER_EMAIL;
const PASSWORD = process.env.E2E_OWNER_PASSWORD;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const REF = `BCO-E2E-${Date.now()}`; // una referencia bancaria acredita un solo pedido

const results = [];
function check(scenario, name, ok, detail = "") {
  results.push({ scenario, name, ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"} [${scenario}] ${name}${detail ? " — " + detail : ""}`);
}

// --- Salvaguardas: sólo loopback y backend local de prueba ------------------------------------
for (const u of [API, WEB]) {
  if (!["127.0.0.1", "localhost", "[::1]"].includes(new URL(u).hostname)) {
    console.error(`Abortado: ${u} no es local. Este harness sólo corre contra servicios locales.`);
    process.exit(2);
  }
}
const health = await fetch(`${API}/health`).then((r) => r.json()).catch(() => null);
if (!health || health.app_env !== "local" || health.payments?.provider !== "simulated" || health.llm?.mode !== "mock") {
  console.error("Abortado: el backend debe estar en APP_ENV=local, PAYMENT_PROVIDER=simulated y LLM_PROVIDER=mock.");
  process.exit(2);
}
if (!EMAIL || !PASSWORD) {
  console.error("Abortado: definí E2E_OWNER_EMAIL y E2E_OWNER_PASSWORD (dueño de la tienda C en la base de prueba).");
  process.exit(2);
}

const launch = process.env.E2E_CHROME_PATH
  ? { executablePath: process.env.E2E_CHROME_PATH }
  : { channel: process.env.E2E_CHROME_CHANNEL || "chrome" };
const browser = await chromium.launch({ ...launch, headless: process.env.E2E_HEADED !== "1" });
const urls = [];
const isChat = (u) => new URL(u).pathname.endsWith("/chat");

async function newPage(options = {}) {
  const ctx = await browser.newContext({ acceptDownloads: true, ...options });
  const page = await ctx.newPage();
  page.on("request", (r) => urls.push(r.url()));
  return { ctx, page };
}

async function send(page, text) {
  const resp = page.waitForResponse((r) => isChat(r.url()) && r.request().method() === "POST", { timeout: 20000 });
  await page.fill('input[aria-label="Mensaje"]', text);
  await page.press('input[aria-label="Mensaje"]', "Enter");
  const r = await resp;
  await page.waitForSelector(".typing", { state: "detached", timeout: 20000 });
  return r.ok() ? r.json() : null;
}

/** Comprobante sintético dibujado en el navegador (PNG), sin archivos del equipo. */
async function receiptPng(page, amount) {
  const b64 = await page.evaluate((amount) => {
    const c = document.createElement("canvas");
    c.width = 900;
    c.height = 330;
    const g = c.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = "#000";
    g.font = "32px sans-serif";
    // La hora hace único el archivo: el mismo comprobante no se acepta en dos pedidos.
    ["Comprobante de transferencia", `Importe: $ ${amount}`, "N de operacion: 77889900112", `Hora: ${Date.now()}`]
      .forEach((t, i) => g.fillText(t, 30, 60 + i * 70));
    return c.toDataURL("image/png").split(",")[1];
  }, amount);
  return { name: "comprobante.png", mimeType: "image/png", buffer: Buffer.from(b64, "base64") };
}

async function download(page, click) {
  const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 15000 }), click()]);
  const chunks = [];
  for await (const c of await dl.createReadStream()) chunks.push(c);
  return { name: dl.suggestedFilename(), data: Buffer.concat(chunks) };
}

const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

try {
  // C1 — el comprador arma un pedido y adjunta su comprobante: queda recibido, sin pagar.
  const B = await newPage();
  await B.page.goto(`${WEB}/#/tienda/${C}`);
  await B.page.waitForSelector(".chatlog");
  await send(B.page, "Busco un flexible de 40 cm");
  await send(B.page, "agregame la 1");
  await send(B.page, "comprar");
  const confirmed = await send(B.page, "sí");
  const order = confirmed?.orders?.[0];
  const convId = confirmed?.conversation_id;
  check("C1", "Pedido confirmado y esperando el pago", order?.status === "PENDING_PAYMENT", order?.status);
  const amount = order ? order.total.toLocaleString("es-AR", { minimumFractionDigits: 2 }) : "0";
  const upload = B.page.waitForResponse((r) => r.url().includes("/documents") && r.request().method() === "POST");
  await B.page.locator("aside.rail input[type=file]").first().setInputFiles(await receiptPng(B.page, amount));
  const up = await upload;
  check("C1", "Subida aceptada", up.status() === 200, `status ${up.status()}`);
  await B.page.waitForSelector("text=Recibimos tu comprobante");
  const read = await B.page.waitForSelector("text=lo revisa el negocio", { timeout: 45000 }).catch(() => null);
  check("C1", "El comprobante se lee en segundo plano (worker)", read);
  const status = await B.page.evaluate(async ({ API, C, convId }) => {
    const ref = JSON.parse(sessionStorage.getItem(`pv.tienda.${C}.conversacion`));
    const own = await fetch(`${API}/public/${C}/conversations/${convId}`, { headers: { "x-conversation-token": ref.token } });
    return (await own.json()).orders[0].status;
  }, { API, C, convId });
  check("C1", "Un comprobante NO marca el pedido como pagado", status === "PENDING_PAYMENT", status);
  check("C1", "El chat no muestra el texto leído del archivo", !(await B.page.locator(".chatlog").innerText()).includes("77889900112"));

  // C2 — el dueño revisa y confirma la transferencia (doble clic no duplica).
  const O = await newPage();
  await O.page.goto(`${WEB}/#/login`);
  await O.page.fill('input[name="email"]', EMAIL);
  await O.page.fill('input[name="password"]', PASSWORD);
  await O.page.press('input[name="password"]', "Enter");
  await O.page.waitForFunction(() => location.hash !== "#/login", null, { timeout: 15000 });
  await O.page.goto(`${WEB}/#/pedidos`);
  const row = O.page.locator(".orders > div", { hasText: `#${order.number}` }).first();
  await row.waitFor();
  const docRow = O.page.locator(".orow", { hasText: `Pedido #${order.number}` }).first();
  check("C2", "El dueño ve el comprobante leído", /Leído/.test(await docRow.innerText()));
  await row.getByRole("button", { name: "Confirmar transferencia" }).click();
  await row.locator('input[placeholder="Nº de operación del banco"]').fill(REF);
  check("C2", "El comprobante del pedido viene tildado para asociar", await row.locator("input[type=checkbox]").first().isChecked());
  await row.locator("form button[type=submit]").dblclick();
  await row.locator(".pill", { hasText: "pagado" }).waitFor({ timeout: 15000 });
  check("C2", "El pedido queda pagado", true);
  await O.page.waitForSelector(".pill:has-text('Asociado al pago')");
  check("C2", "El comprobante queda asociado al pago", true);

  // C3 — el comprador recibe UNA constancia y la descarga; recargar no duplica.
  await B.page.reload();
  await B.page.waitForSelector(".chatlog");
  await sleep(1000);
  const receiptButtons = await B.page.locator(".chatlog button", { hasText: "Descargar constancia" }).count();
  check("C3", "Un solo mensaje de constancia tras doble clic y recarga", receiptButtons === 1, `${receiptButtons}`);
  const pdf = await download(B.page, () => B.page.locator(".chatlog button", { hasText: "Descargar constancia" }).click());
  check("C3", "Descarga un PDF de constancia", pdf.data.subarray(0, 5).toString() === "%PDF-" && /constancia-pedido-/.test(pdf.name), pdf.name);
  check("C3", "El comprobante figura asociado", /asociado al pago confirmado/.test(await B.page.locator("aside.rail").innerText()));
  const foreign = await B.page.evaluate(async ({ API, C, convId }) => {
    const ref = JSON.parse(sessionStorage.getItem(`pv.tienda.${C}.conversacion`));
    const own = await fetch(`${API}/public/${C}/conversations/${convId}`, { headers: { "x-conversation-token": ref.token } })
      .then((r) => r.json());
    const receipt = own.orders[0].receipt_id;
    const conv = await fetch(`${API}/public/${C}/conversations/${convId}`);
    const pdf = await fetch(`${API}/public/${C}/conversations/${convId}/receipts/${receipt}/pdf`);
    return [conv.status, pdf.status];
  }, { API, C, convId });
  check("C3", "Sin token no se abren la conversación ni la constancia", foreign[0] === 404 && foreign[1] === 404,
    `status ${foreign}`);

  // C4 — registro mensual desde el panel.
  const csv = await download(O.page, () => O.page.getByRole("button", { name: "Registro del mes (CSV)" }).click());
  const text = csv.data.toString("utf8");
  check("C4", "CSV con BOM, el pago y su origen", text.startsWith("﻿") && text.includes(REF) && text.includes("Transferencia"));

  // C5 — ancho de celular (390 px) para comprador y dueño.
  for (const [who, url] of [["comprador", `${WEB}/#/tienda/${C}`], ["dueño", `${WEB}/#/pedidos`]]) {
    const ctx = who === "comprador" ? B.ctx : O.ctx;
    const page = await ctx.newPage();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    const extra = await overflow(page);
    check("C5", `Sin desborde horizontal a 390 px (${who})`, extra <= 0, `${extra}px`);
    await page.close();
  }

  check("C6", "Ningún token de comprador en las URLs", !urls.some((u) => /token=/i.test(u)));
} catch (e) {
  check("—", "Error inesperado", false, e?.stack || String(e));
} finally {
  await browser.close();
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} comprobaciones OK`);
process.exit(failed.length ? 1 : 0);
