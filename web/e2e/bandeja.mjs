// Aceptación en navegador de la bandeja (roadmap etapa 2): el cliente pide una persona, el dueño
// toma el control, el asistente se calla, el dueño responde y devuelve la conversación.
// Opera SÓLO sobre servicios locales (loopback) con una base de prueba y el seed sintético C.
// Instrucciones: e2e/README.md.  Uso: E2E_OWNER_EMAIL=… E2E_OWNER_PASSWORD=… npm run e2e:bandeja
import { chromium } from "playwright-core";

const API = process.env.E2E_API || "http://127.0.0.1:8077";
const WEB = process.env.E2E_WEB || "http://127.0.0.1:4173";
const C = "sanitarios-demo-c";
const EMAIL = process.env.E2E_OWNER_EMAIL;
const PASSWORD = process.env.E2E_OWNER_PASSWORD;
const RUN = Date.now();

const results = [];
function check(scenario, name, ok, detail = "") {
  results.push({ ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"} [${scenario}] ${name}${detail ? " — " + detail : ""}`);
}

for (const u of [API, WEB]) {
  if (!["127.0.0.1", "localhost", "[::1]"].includes(new URL(u).hostname)) {
    console.error(`Abortado: ${u} no es local.`);
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
const isChat = (u) => new URL(u).pathname.endsWith("/chat");

async function send(page, text) {
  const resp = page.waitForResponse((r) => isChat(r.url()) && r.request().method() === "POST", { timeout: 20000 });
  await page.fill('input[aria-label="Mensaje"]', text);
  await page.press('input[aria-label="Mensaje"]', "Enter");
  const r = await resp;
  await page.waitForSelector(".typing", { state: "detached", timeout: 20000 });
  return r.ok() ? r.json() : null;
}
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

try {
  // B1 — el cliente pide una persona.
  const bctx = await browser.newContext();
  const B = await bctx.newPage();
  await B.goto(`${WEB}/#/tienda/${C}`);
  await B.waitForSelector(".chatlog");
  const first = await send(B, "quiero hablar con una persona");
  const conv = first?.conversation_id;
  check("B1", "El asistente registra la derivación", first?.requires_human === true);

  // B2 — el dueño la ve en «Derivadas», la abre y toma el control.
  const octx = await browser.newContext();
  const O = await octx.newPage();
  await O.goto(`${WEB}/#/login`);
  await O.fill('input[name="email"]', EMAIL);
  await O.fill('input[name="password"]', PASSWORD);
  await O.press('input[name="password"]', "Enter");
  await O.waitForFunction(() => location.hash !== "#/login", null, { timeout: 15000 });
  await O.goto(`${WEB}/#/conversaciones`);
  const item = O.locator(`[data-conversation="${conv}"]`);
  await item.waitFor({ timeout: 15000 });
  check("B2", "Aparece en Derivadas con «Pidió una persona»", /Pidió una persona/.test(await item.innerText()));
  await item.click();
  await O.getByRole("button", { name: "Tomar el control" }).click();
  await O.getByRole("button", { name: "Devolver al asistente" }).waitFor();
  check("B2", "Toma el control", true);

  // B3 — con el control tomado, el asistente no responde y el cliente ve que lo atiende una persona.
  const before = await B.locator(".chatlog .bubble.bot").count();
  const held = await send(B, `¿cuánto sale el envío a Rosario? ref ${RUN}`);
  check("B3", "El asistente no responde", held?.mode === "human" && held?.reply === "");
  await B.waitForSelector("text=Te está atendiendo una persona del negocio");
  check("B3", "Sin burbuja del asistente", (await B.locator(".chatlog .bubble.bot").count()) === before);

  // B4 — el dueño ve el mensaje y responde; al cliente le llega como «Equipo de …».
  await O.waitForSelector(`text=ref ${RUN}`, { timeout: 15000 });
  check("B4", "El dueño ve el mensaje nuevo del cliente", true);
  await O.fill('input[aria-label="Respuesta"]', `Hola, soy Ana del local. A Rosario sale $5.000 (${RUN}).`);
  await O.press('input[aria-label="Respuesta"]', "Enter");
  await B.waitForSelector(`text=A Rosario sale $5.000 (${RUN})`, { timeout: 15000 });
  const author = await B.locator(".msg-author").last().innerText();
  check("B4", "El cliente recibe la respuesta del equipo", /^Equipo de /.test(author), author);

  // B5 — devuelve la conversación: el asistente vuelve a responder.
  await O.getByRole("button", { name: "Devolver al asistente" }).click();
  await O.getByRole("button", { name: "Tomar el control" }).waitFor();
  await B.reload();
  await B.waitForSelector(".chatlog");
  const back = await send(B, "busco un flexible de 40 cm");
  check("B5", "El asistente vuelve a responder", back?.mode !== "human" && !!back?.reply);
  check("B5", "Sin aviso de atención humana", (await B.locator("text=Te está atendiendo").count()) === 0);

  // B6 — 390 px.
  for (const [who, ctx, url] of [["cliente", bctx, `${WEB}/#/tienda/${C}`], ["dueño", octx, `${WEB}/#/conversaciones`]]) {
    const p = await ctx.newPage();
    await p.setViewportSize({ width: 390, height: 844 });
    await p.goto(url);
    await p.waitForLoadState("networkidle");
    if (who === "dueño") {
      await p.locator(`[data-conversation="${conv}"]`).click().catch(() => {});
      await p.waitForTimeout(500);
    }
    const extra = await overflow(p);
    check("B6", `Sin desborde horizontal a 390 px (${who})`, extra <= 0, `${extra}px`);
    await p.close();
  }
} catch (e) {
  check("—", "Error inesperado", false, e?.stack || String(e));
} finally {
  await browser.close();
}

const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} comprobaciones OK`);
process.exit(failed ? 1 : 0);
