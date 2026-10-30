// Aceptación en navegador del asistente paso a paso (roadmap etapa 6): el dueño cambia cómo habla
// su agente, lo prueba en la vista previa SIN publicar, publica y la tienda responde así.
// Opera SÓLO sobre servicios locales (loopback) con una base de prueba y el seed sintético C.
// Instrucciones: e2e/README.md.  Uso: E2E_OWNER_EMAIL=… E2E_OWNER_PASSWORD=… npm run e2e:asistente
import { chromium } from "playwright-core";

const API = process.env.E2E_API || "http://127.0.0.1:8077";
const WEB = process.env.E2E_WEB || "http://127.0.0.1:4173";
const C = "sanitarios-demo-c";
const EMAIL = process.env.E2E_OWNER_EMAIL;
const PASSWORD = process.env.E2E_OWNER_PASSWORD;
const GREETING = `Hola, soy Ramona (${Date.now()}). ¿Qué estás buscando?`;

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
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
const storeGreeting = () => fetch(`${API}/public/${C}`).then((r) => r.json()).then((j) => j.greeting);

try {
  const ctx = await browser.newContext();
  const O = await ctx.newPage();
  O.setDefaultTimeout(15000);
  await O.goto(`${WEB}/#/login`);
  await O.fill('input[name="email"]', EMAIL);
  await O.fill('input[name="password"]', PASSWORD);
  await O.press('input[name="password"]', "Enter");
  await O.waitForFunction(() => location.hash !== "#/login");
  await O.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith("pv.asistente.")).forEach((k) => localStorage.removeItem(k)));
  await O.goto(`${WEB}/#/asistente`);
  await O.waitForSelector(".wizard-steps");
  check("A1", "El asistente muestra los 8 pasos", (await O.locator(".wizard-step").count()) === 8);
  check("A1", "El catálogo del negocio cuenta como paso listo",
    /✓/.test(await O.locator(".wizard-step", { hasText: "Catálogo" }).innerText()));

  // A1b — elegir un rubro sólo cambia el borrador: la tienda no cambia hasta publicar.
  const greetingBefore = await storeGreeting();
  O.once("dialog", (d) => d.accept());
  await O.locator(".wizard-step", { hasText: "Rubro" }).click();
  await O.locator(".wizard-option").first().click();
  await O.waitForSelector(".wizard-option[aria-pressed=true]");
  check("A1", "Elegir rubro no publica nada", (await storeGreeting()) === greetingBefore);

  // A2 — cambia el saludo (borrador) y lo prueba sin publicar.
  await O.locator(".wizard-step", { hasText: "Cómo habla" }).click();
  await O.locator("textarea").first().fill(GREETING);
  await O.reload();                                           // el borrador sobrevive a una recarga
  await O.waitForSelector(".wizard-card");
  check("A2", "El borrador se conserva al recargar", (await O.locator("textarea").first().inputValue()) === GREETING);
  await O.locator(".wizard-step", { hasText: "Probar" }).click();
  const preview = O.waitForResponse((r) => r.url().endsWith("/app/agent-preview"));
  await O.getByRole("button", { name: "Hola", exact: true }).click();
  check("A2", "La vista previa responde", (await preview).ok());
  await O.waitForSelector(`.wizard-preview .bubble.bot >> text=${GREETING}`);
  check("A2", "Responde con el saludo del borrador", true);
  check("A2", "Avisa que responde por reglas (sin IA)",
    (await O.locator(".wizard-preview .msg-author", { hasText: "sin IA" }).count()) === 1);
  check("A2", "La tienda todavía no cambió", (await storeGreeting()) !== GREETING);

  // A3 — publica: la tienda responde con lo configurado.
  await O.locator(".wizard-step", { hasText: "Publicar" }).click();
  await O.getByRole("button", { name: "Publicar", exact: true }).click();
  const igual = O.getByRole("button", { name: "Publicar igual" });
  await Promise.race([O.waitForSelector("text=¡Publicado!"), igual.waitFor()]);
  if (await igual.isVisible()) await igual.click();       // pruebas del negocio que fallan: decide el dueño
  await O.waitForSelector("text=¡Publicado!");
  check("A3", "Publica", true);
  check("A3", "La tienda usa el saludo nuevo", (await storeGreeting()) === GREETING);
  check("A3", "Ofrece el link de la tienda", (await O.locator(".wizard-url").innerText()).endsWith(`#/tienda/${C}`));
  const B = await (await browser.newContext()).newPage();
  await B.goto(`${WEB}/#/tienda/${C}`);
  await B.waitForSelector(".chatlog");
  check("A3", "El cliente ve el saludo nuevo", (await B.locator(".chatlog .bubble.bot").first().innerText()) === GREETING);

  // A4 — 390 px.
  const M = await ctx.newPage();
  await M.setViewportSize({ width: 390, height: 844 });
  for (const s of ["Negocio", "Probar", "Publicar"]) {
    await M.goto(`${WEB}/#/asistente`);
    await M.waitForSelector(".wizard-steps");
    await M.locator(".wizard-step", { hasText: s }).click();
    const extra = await overflow(M);
    check("A4", `Sin desborde horizontal a 390 px (${s})`, extra <= 0, `${extra}px`);
  }
} catch (e) {
  check("—", "Error inesperado", false, e?.stack || String(e));
} finally {
  await browser.close();
}

const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} comprobaciones OK`);
process.exit(failed ? 1 : 0);
