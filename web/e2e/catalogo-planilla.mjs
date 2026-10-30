// Aceptación en navegador de «Planilla de Google» en Catálogo: rechaza links de otros sitios,
// informa con claridad una planilla que no se puede leer y permite desconectar.
// La lectura exitosa la cubren los tests del backend (transporte falso). Este e2e SÍ consulta a
// Google con un ID inexistente para comprobar el mensaje real. Sólo servicios locales.
// Uso: E2E_OWNER_EMAIL=… E2E_OWNER_PASSWORD=… npm run e2e:planilla
import { chromium } from "playwright-core";

const API = process.env.E2E_API || "http://127.0.0.1:8077";
const WEB = process.env.E2E_WEB || "http://127.0.0.1:4173";
const EMAIL = process.env.E2E_OWNER_EMAIL;
const PASSWORD = process.env.E2E_OWNER_PASSWORD;
const FAKE = "https://docs.google.com/spreadsheets/d/1NoExisteEstaPlanillaDePruebaE2E_xyz/edit#gid=0";

const results = [];
function check(scenario, name, ok, detail = "") {
  results.push({ ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"} [${scenario}] ${name}${detail ? " — " + detail : ""}`);
}
for (const u of [API, WEB]) {
  if (!["127.0.0.1", "localhost", "[::1]"].includes(new URL(u).hostname)) { console.error(`Abortado: ${u} no es local.`); process.exit(2); }
}
const health = await fetch(`${API}/health`).then((r) => r.json()).catch(() => null);
if (!health || health.app_env !== "local" || health.llm?.mode !== "mock") {
  console.error("Abortado: el backend debe estar en APP_ENV=local y LLM_PROVIDER=mock."); process.exit(2);
}
if (!EMAIL || !PASSWORD) { console.error("Abortado: definí E2E_OWNER_EMAIL y E2E_OWNER_PASSWORD."); process.exit(2); }

const launch = process.env.E2E_CHROME_PATH ? { executablePath: process.env.E2E_CHROME_PATH } : { channel: process.env.E2E_CHROME_CHANNEL || "chrome" };
const browser = await chromium.launch({ ...launch, headless: process.env.E2E_HEADED !== "1" });
try {
  const p = await (await browser.newContext()).newPage();
  p.setDefaultTimeout(30000);
  await p.goto(`${WEB}/#/login`);
  await p.fill('input[name="email"]', EMAIL);
  await p.fill('input[name="password"]', PASSWORD);
  await p.press('input[name="password"]', "Enter");
  await p.waitForFunction(() => location.hash !== "#/login");
  await p.goto(`${WEB}/#/catalogo`);
  const card = p.locator('section[aria-label="Planilla de Google"]');
  await card.waitFor();
  if (await card.getByRole("button", { name: "Desconectar" }).count()) {      // estado de una corrida anterior
    p.once("dialog", (d) => d.accept());
    await card.getByRole("button", { name: "Desconectar" }).click();
    await card.getByRole("button", { name: "Conectar" }).waitFor();
  }
  check("P1", "Muestra cómo compartir la planilla", /Cualquier persona con el enlace/.test(await card.innerText()));

  await card.getByLabel("Link de la planilla").fill("https://evil.example.com/spreadsheets/d/1234567890123456789012");
  await card.getByRole("button", { name: "Conectar" }).click();
  await card.locator(".state.err").waitFor();
  check("P2", "Rechaza un link que no es de Google Sheets", /docs\.google\.com\/spreadsheets/.test(await card.locator(".state.err").innerText()));
  check("P2", "No queda nada conectado", (await card.getByRole("button", { name: "Conectar" }).count()) === 1);

  await card.getByLabel("Link de la planilla").fill(FAKE);
  await card.getByRole("button", { name: "Conectar" }).click();
  await card.getByText("No se pudo leer").waitFor();
  const msg = await card.locator(".state.err").first().innerText();
  check("P3", "Una planilla que no se puede leer se informa con un mensaje claro", /compartila|privada|Google|conectarme/.test(msg), msg);

  p.once("dialog", (d) => d.accept());
  await card.getByRole("button", { name: "Desconectar" }).click();
  await card.getByRole("button", { name: "Conectar" }).waitFor();
  check("P4", "Desconecta", true);
} catch (e) {
  check("—", "Error inesperado", false, e?.stack || String(e));
} finally {
  await browser.close();
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} comprobaciones OK`);
process.exit(failed ? 1 : 0);
