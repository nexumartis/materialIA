// Aceptación en navegador del chat público (privado, recuperable, resistente a respuestas tardías).
// Opera SÓLO sobre servicios locales (loopback) con la base de prueba y el seed sintético C/D.
// Instrucciones: e2e/README.md.  Uso: npm run e2e
import { chromium } from "playwright-core";

const API = process.env.E2E_API || "http://127.0.0.1:8077";
const WEB = process.env.E2E_WEB || "http://127.0.0.1:4173";
const C = "sanitarios-demo-c"; // tiendas públicas del seed (datos sintéticos)
const D = "ferreteria-demo-d";
const KEY = (slug) => `pv.tienda.${slug}.conversacion`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const results = [];
function check(scenario, name, ok, detail = "") {
  results.push({ scenario, name, ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"} [${scenario}] ${name}${detail ? " — " + detail : ""}`);
}

// --- Salvaguardas: sólo loopback y backend local de prueba ------------------------------------
for (const u of [API, WEB]) {
  const host = new URL(u).hostname;
  if (!["127.0.0.1", "localhost", "[::1]"].includes(host)) {
    console.error(`Abortado: ${u} no es local. Este harness sólo corre contra servicios locales.`);
    process.exit(2);
  }
}
const health = await fetch(`${API}/health`).then((r) => r.json()).catch(() => null);
if (!health || health.app_env !== "local" || health.payments?.provider !== "simulated" || health.llm?.mode !== "mock") {
  console.error("Abortado: el backend debe estar en APP_ENV=local, PAYMENT_PROVIDER=simulated y LLM_PROVIDER=mock.",
    health ? JSON.stringify({ app_env: health.app_env, payments: health.payments, llm: health.llm?.mode }) : "(sin /health)");
  process.exit(2);
}

const launch = process.env.E2E_CHROME_PATH
  ? { executablePath: process.env.E2E_CHROME_PATH }
  : { channel: process.env.E2E_CHROME_CHANNEL || "chrome" };
const browser = await chromium.launch({ ...launch, headless: process.env.E2E_HEADED !== "1" });

const urls = [];
const consoleLines = [];
const tokens = new Set();
const isChat = (u) => new URL(u).pathname.endsWith("/chat");

async function newPage(options = {}) {
  const ctx = await browser.newContext(options);
  const page = await ctx.newPage();
  page.on("request", (r) => urls.push(r.url()));
  page.on("console", (m) => consoleLines.push(m.text()));
  page.on("response", async (r) => {
    if (isChat(r.url()) && r.request().method() === "POST" && r.ok()) {
      try {
        const j = await r.json();
        if (j.conversation_token) tokens.add(j.conversation_token);
      } catch {
        /* respuesta interceptada o sin JSON */
      }
    }
  });
  return { ctx, page };
}

const open = (page, slug) => page.goto(`${WEB}/#/tienda/${slug}`).then(() => page.waitForSelector(".chatlog"));
const goStore = async (page, slug) => {
  await page.evaluate((h) => (location.hash = h), `#/tienda/${slug}`);
  await page.waitForSelector(".chatlog");
};
const msgCount = (page) => page.locator(".chatlog .msg").count();
const stored = (page, slug) => page.evaluate((k) => sessionStorage.getItem(k), KEY(slug));
const logText = (page) => page.locator(".chatlog").innerText();

async function send(page, text, { wait = true } = {}) {
  const resp = page
    .waitForResponse((r) => isChat(r.url()) && r.request().method() === "POST", { timeout: 20000 })
    .catch(() => null);
  await page.fill('input[aria-label="Mensaje"]', text);
  await page.press('input[aria-label="Mensaje"]', "Enter");
  if (!wait) return null;
  const r = await resp;
  await page.waitForSelector(".typing", { state: "detached", timeout: 20000 });
  try {
    return r && r.ok() ? await r.json() : null;
  } catch {
    return null;
  }
}

// Demora una ruta: "late" deja que el servidor procese y entrega la respuesta tarde;
// "fail" corta la conexión; "404" responde 404 tarde.
function delayRoute(page, pattern, ms, mode = "late", capture) {
  return page.route(pattern, async (route) => {
    await (mode === "late" ? Promise.resolve() : sleep(ms));
    if (mode === "fail") return route.abort("failed");
    if (mode === "404") {
      return route.fulfill({ status: 404, contentType: "application/json",
        headers: { "access-control-allow-origin": "*" }, body: '{"detail":"Conversación no encontrada."}' });
    }
    const resp = await route.fetch();
    if (capture) {
      try {
        capture(await resp.json());
      } catch {
        /* sin JSON */
      }
    }
    await sleep(ms);
    return route.fulfill({ response: resp });
  });
}

let aConv = null;
try {
  // S1 — dos compradores de la misma tienda: B no ve ni opera la conversación de A.
  {
    const A = await newPage();
    await open(A.page, C);
    const r1 = await send(A.page, "Busco un flexible de 40 cm");
    aConv = r1 && r1.conversation_id;
    await send(A.page, "agregame la 1");
    const B = await newPage();
    await open(B.page, C);
    check("S1", "B abre la tienda y no ve mensajes de A", (await msgCount(B.page)) === 0);
    const probe = await B.page.evaluate(async ({ API, C, aConv }) => {
      const g = await fetch(`${API}/public/${C}/conversations/${aConv}`);
      const p = await fetch(`${API}/public/${C}/chat`, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: "comprar", conversation_id: aConv }) });
      const s = await fetch(`${API}/sandbox/sales/${aConv}?company=C`);
      return { get: g.status, post: p.status, sandbox: s.status };
    }, { API, C, aConv });
    check("S1", "B con la UUID de A: GET rechazado", probe.get === 404, `status ${probe.get}`);
    check("S1", "B con la UUID de A: POST rechazado", probe.post === 404, `status ${probe.post}`);
    check("S1", "Sandbox no abre la conversación pública de A", probe.sandbox === 404, `status ${probe.sandbox}`);

    // S2 — compra, pago simulado en otra pestaña y recarga: vuelve la conversación y el pedido pagado.
    // Consume 1 unidad del flexible sintético del seed C por corrida.
    await send(A.page, "comprar");
    const last = await send(A.page, "sí");
    const href = await A.page.locator("a.paybtn").last().getAttribute("href");
    const orderId = last && last.orders && last.orders[0] && last.orders[0].id;
    const pay = await A.ctx.newPage();
    await pay.goto(href);
    await pay.click("text=Pagar (aprobado)");
    await pay.waitForSelector("text=Pago aprobado");
    await pay.close();
    const before = await msgCount(A.page);
    await A.page.reload();
    await A.page.waitForSelector(".chatlog");
    await sleep(1500);
    const after = await msgCount(A.page);
    const rail = await A.page.locator("aside.rail").innerText();
    check("S2", "Recarga tras checkout recupera los mensajes", after >= before && after >= 8, `antes ${before}, después ${after}`);
    check("S2", "Recarga tras checkout muestra el pedido pagado", /pagado/i.test(rail));
    const viaSandbox = await B.page.evaluate(async ({ API, orderId }) => (await fetch(`${API}/sandbox/orders/${orderId}?company=C`)).status, { API, orderId });
    check("S2", "El pedido de A no se lee por la ruta sandbox", !!orderId && viaSandbox === 404, `status ${viaSandbox}`);
    await A.ctx.close();
    await B.ctx.close();
  }

  // S3/S6 — A → B → A, y cambio de tienda con respuesta pendiente.
  {
    const P = await newPage();
    await open(P.page, C);
    await send(P.page, "canilla negra de cocina");
    const cConv = JSON.parse((await stored(P.page, C)) || "null");
    let late = null;
    await delayRoute(P.page, `**/public/${C}/chat`, 2500, "late", (j) => (late = j));
    await send(P.page, "agregame la 1", { wait: false });
    await sleep(400);
    await goStore(P.page, D);
    await sleep(3200);
    await P.page.unroute(`**/public/${C}/chat`);
    check("S6", "Respuesta tardía de C no aparece en D", (await msgCount(P.page)) === 0 && !(await logText(P.page)).includes("agregame"));
    check("S6", "D no hereda la referencia de C", (await stored(P.page, D)) === null);
    check("S6", "La respuesta tardía efectivamente llegó", late !== null);
    await send(P.page, "busco tornillos para madera");
    const dConv = JSON.parse((await stored(P.page, D)) || "null");
    await goStore(P.page, C);
    await sleep(1500);
    const cText = await logText(P.page);
    check("S3", "Volver a C recupera la conversación de C", (await msgCount(P.page)) >= 2 && cText.includes("canilla negra de cocina"));
    check("S3", "C no muestra mensajes de D", !cText.includes("tornillos"));
    check("S3", "Referencias distintas por tienda", !!cConv && !!dConv && cConv.id !== dConv.id);
    await goStore(P.page, D);
    await sleep(1500);
    const dText = await logText(P.page);
    check("S3", "Volver a D recupera la conversación de D", dText.includes("tornillos") && !dText.includes("canilla negra"));
    await P.ctx.close();
  }

  // S4 — POST demorado + "Nueva conversación".
  {
    const P = await newPage();
    await open(P.page, C);
    let late = null;
    await delayRoute(P.page, `**/public/${C}/chat`, 2500, "late", (j) => (late = j));
    await send(P.page, "canilla negra de cocina", { wait: false });
    await sleep(400);
    await P.page.click("text=Nueva conversación");
    await sleep(3200);
    await P.page.unroute(`**/public/${C}/chat`);
    check("S4", "POST tardío no repuebla la vista", (await msgCount(P.page)) === 0);
    check("S4", "POST tardío no guarda referencia", (await stored(P.page, C)) === null);
    const reqBody = P.page.waitForRequest((r) => isChat(r.url()) && r.method() === "POST");
    const next = await send(P.page, "hola");
    const body = JSON.parse((await reqBody).postData() || "{}");
    check("S4", "El siguiente envío crea otra conversación",
      body.conversation_id === null && !!next && !!late && next.conversation_id !== late.conversation_id);
    check("S4", "La vista del nuevo hilo tiene sólo su turno", (await msgCount(P.page)) === 2);
    await P.ctx.close();
  }
  // S4b — POST demorado que FALLA + reinicio: el error viejo no aparece.
  {
    const P = await newPage();
    await open(P.page, C);
    await delayRoute(P.page, `**/public/${C}/chat`, 2000, "fail");
    await send(P.page, "canilla negra de cocina", { wait: false });
    await sleep(400);
    await P.page.click("text=Nueva conversación");
    await sleep(2600);
    check("S4b", "Error tardío no aparece tras reiniciar", (await msgCount(P.page)) === 0);
    await P.ctx.close();
  }

  // S5 — GET demorado (restauración al recargar) + reinicio.
  {
    const P = await newPage();
    await open(P.page, C);
    await send(P.page, "canilla negra de cocina");
    await delayRoute(P.page, "**/conversations/**", 2500, "late");
    await P.page.reload();
    await P.page.waitForSelector(".chatlog");
    await sleep(400);
    await P.page.click("text=Nueva conversación");
    await sleep(3200);
    check("S5", "GET tardío no repuebla la vista", (await msgCount(P.page)) === 0);
    check("S5", "GET tardío no restaura la referencia", (await stored(P.page, C)) === null);
    await P.ctx.close();
  }
  // S5b — GET demorado que falla (404) cuando ya empezó otra conversación.
  {
    const P = await newPage();
    await open(P.page, C);
    await send(P.page, "canilla negra de cocina");
    await delayRoute(P.page, "**/conversations/**", 3000, "404");
    await P.page.reload();
    await P.page.waitForSelector(".chatlog");
    await sleep(300);
    await P.page.click("text=Nueva conversación");
    const fresh = await send(P.page, "hola");
    await sleep(3500);
    const ref = JSON.parse((await stored(P.page, C)) || "null");
    check("S5b", "404 tardío no borra la conversación nueva (vista)", (await msgCount(P.page)) === 2);
    check("S5b", "404 tardío no borra la conversación nueva (referencia)", !!ref && !!fresh && ref.id === fresh.conversation_id);
    await P.ctx.close();
  }

  // S7 — referencia guardada inexistente o ajena: se descarta sin bucles.
  {
    const P = await newPage();
    await open(P.page, C);
    for (const [label, ref] of [["inexistente", { id: "99999999-9999-9999-9999-999999999999", token: "x" }],
                                ["UUID ajena con token falso", { id: aConv, token: "token-falso" }]]) {
      await P.page.evaluate(([k, v]) => sessionStorage.setItem(k, v), [KEY(C), JSON.stringify(ref)]);
      let gets = 0;
      const on = (r) => {
        if (r.url().includes("/conversations/")) gets++;
      };
      P.page.on("request", on);
      await P.page.reload();
      await P.page.waitForSelector(".chatlog");
      await sleep(2500);
      P.page.off("request", on);
      check("S7", `Ref ${label}: vista vacía`, (await msgCount(P.page)) === 0);
      check("S7", `Ref ${label}: referencia descartada`, (await stored(P.page, C)) === null);
      check("S7", `Ref ${label}: sin bucle (1 GET)`, gets === 1, `GETs ${gets}`);
    }
    await P.ctx.close();
  }

  // S8 — el chat demo del sandbox sigue funcionando.
  {
    const P = await newPage();
    await P.page.goto(`${WEB}/#/venta`);
    await P.page.waitForSelector(".chatlog");
    const r = await send(P.page, "canilla negra de cocina");
    check("S8", "Chat demo #/venta responde", !!r && (await msgCount(P.page)) === 2);
    await P.ctx.close();
  }

  // S10 — ancho de celular (390 px): sin desborde horizontal, composer y tarjetas a la vista.
  {
    const P = await newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    await open(P.page, C);
    await send(P.page, "Busco un flexible de 40 cm");
    const m = await P.page.evaluate(() => {
      const box = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { left: r.left, right: r.right };
      };
      return { scroll: document.documentElement.scrollWidth, width: window.innerWidth,
               input: box('input[aria-label="Mensaje"]'), card: box(".pcard") };
    });
    check("S10", "Sin desborde horizontal a 390 px", m.scroll <= m.width, `scrollWidth ${m.scroll}, ancho ${m.width}`);
    check("S10", "Campo de mensaje dentro de la pantalla", !!m.input && m.input.left >= 0 && m.input.right <= m.width);
    check("S10", "Tarjeta de producto dentro de la pantalla", !!m.card && m.card.left >= 0 && m.card.right <= m.width);
    await P.ctx.close();
  }
} catch (e) {
  check("harness", "sin excepciones", false, String((e && e.stack) || e));
} finally {
  await browser.close();
}

// S9 — ningún token de comprador en URLs ni en la consola.
const leaked = (lines) => lines.filter((l) => [...tokens].some((t) => l.includes(t))).length;
check("S9", "Se emitieron tokens", tokens.size > 0, `${tokens.size}`);
check("S9", "Ningún token en URLs", leaked(urls) === 0, `${urls.length} URLs revisadas`);
check("S9", "Ningún token en consola", leaked(consoleLines) === 0, `${consoleLines.length} líneas`);

const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed} PASS, ${failed} FAIL`);
process.exit(failed ? 1 : 0);
