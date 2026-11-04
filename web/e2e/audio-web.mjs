// Audio del chat público en navegador (nota de voz estilo WhatsApp), con la frontera HTTP del backend
// simulada (datos sintéticos). No usa backend, proveedor de voz, micrófono físico ni el Chrome del
// usuario: abre un Chrome headless propio con dispositivo de audio falso.
// Uso, desde web/ con el build servido (npm run build && npm run preview -- --host 127.0.0.1 --port 5187):
//   CHROME_PATH=<chrome.exe> AUDIO_WEB_URL=http://127.0.0.1:5187 E2E_API=<VITE_API_BASE del build> node e2e/audio-web.mjs
// AUDIO_SHOTS=<dir fuera del repo> guarda capturas de escritorio y móvil.
import { chromium } from "playwright-core";
import { join } from "node:path";

const WEB = process.env.AUDIO_WEB_URL || "http://127.0.0.1:5187";
const API = process.env.E2E_API || "http://127.0.0.1:8077"; // VITE_API_BASE del build; nunca se contacta
const SHOTS = process.env.AUDIO_SHOTS;
const SLUG = "sanitarios-demo-c";
const CONV = "11111111-1111-4111-8111-111111111111";
const TOKEN = "token-sintetico";
const HEARD = "Quiero 3 canillas negras para cocina";
const REPLY = "Tengo la Canilla Negra Cocina a $45.000, 12 disponibles. ¿Te armo el pedido?";
const botId = (n) => `22222222-2222-4222-8222-${String(n).padStart(12, "0")}`;

for (const u of [WEB, API]) {
  if (!["127.0.0.1", "localhost", "[::1]"].includes(new URL(u).hostname)) {
    console.error(`Abortado: ${u} no es local.`);
    process.exit(2);
  }
}
if (!process.env.CHROME_PATH) {
  console.error("Falta CHROME_PATH (ejecutable de Chrome/Chromium para una instancia headless separada).");
  process.exit(2);
}

let failures = 0;
let passes = 0;
function check(name, ok, detail = "") {
  ok ? passes++ : failures++;
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? " — " + detail : ""}`);
}

/** WAV estéreo 44.1 kHz (distinto del formato del backend: obliga a la UI a convertirlo). */
function sineWav(seconds = 1, rate = 44100) {
  const frames = Math.round(seconds * rate);
  const b = Buffer.alloc(44 + frames * 4);
  b.write("RIFF", 0); b.writeUInt32LE(36 + frames * 4, 4); b.write("WAVEfmt ", 8);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(2, 22); b.writeUInt32LE(rate, 24);
  b.writeUInt32LE(rate * 4, 28); b.writeUInt16LE(4, 32); b.writeUInt16LE(16, 34);
  b.write("data", 36); b.writeUInt32LE(frames * 4, 40);
  for (let i = 0; i < frames; i++) {
    const v = Math.round(Math.sin((2 * Math.PI * 440 * i) / rate) * 8000);
    b.writeInt16LE(v, 44 + i * 4); b.writeInt16LE(v, 46 + i * 4);
  }
  return b;
}

function wavInfo(buf) {
  return {
    riff: buf.toString("ascii", 0, 4) === "RIFF" && buf.toString("ascii", 8, 12) === "WAVE",
    format: buf.readUInt16LE(20), channels: buf.readUInt16LE(22), rate: buf.readUInt32LE(24), bits: buf.readUInt16LE(34),
    size: buf.length,
  };
}
const isBackendWav = (c) => {
  const i = wavInfo(c.body);
  return c.headers["content-type"] === "audio/wav" && i.riff && i.format === 1 && i.channels === 1 && i.rate === 16000 && i.bits === 16;
};

/** Backend simulado. `state` se puede cambiar durante la prueba (texto entendido, fallo TTS, demora del chat). */
async function mockBackend(page, state) {
  const log = [];
  const history = [];
  await page.route(`${API}/**`, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const p = url.pathname;
    log.push({ method: req.method(), path: p, search: url.search, headers: req.headers(), body: req.postDataBuffer() });
    const json = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (p === `/public/${SLUG}`) return json({ name: "Sanitarios Demo C", seller_name: "Sofi", greeting: null, payments: "simulated" });
    if (p === `/public/${SLUG}/audio`) {
      return json({ enabled: state.enabled, input_mime: "audio/wav", sample_rate_hz: 16000, channels: 1, sample_width_bits: 16,
        max_upload_bytes: 1_000_000, max_duration_seconds: 30, max_tts_characters: 2000, max_transcript_characters: 2000 });
    }
    if (p === `/public/${SLUG}/audio/transcriptions`) return json({ text: state.heard, duration_seconds: 1 });
    if (p === `/public/${SLUG}/chat`) {
      const { message } = JSON.parse(req.postData());
      await new Promise((r) => setTimeout(r, state.chatDelay ?? 0));
      const n = history.length;
      history.push({ id: `33333333-3333-4333-8333-${String(n).padStart(12, "0")}`, role: "user", content: message, ui: null },
        { id: botId(n + 1), role: "assistant", content: REPLY, ui: null });
      return json({ reply: REPLY, conversation_id: CONV, conversation_token: TOKEN, mode: "mock", requires_human: false,
        cart: null, orders: [], payment: null, trace: [], ui: {} });
    }
    if (p === `/public/${SLUG}/conversations/${CONV}`) return json({ messages: history, cart: null, orders: [], documents: [], attended_by_human: false });
    const tts = p.match(new RegExp(`^/public/${SLUG}/conversations/${CONV}/messages/([^/]+)/audio$`));
    if (tts && history.some((m) => m.id === tts[1] && m.role === "assistant")) {
      if (state.ttsFail) return json({ detail: "El proveedor de voz no pudo completar la solicitud. No se reintenta automáticamente." }, 502);
      return route.fulfill({ status: 200, contentType: "audio/mpeg", body: sineWav(0.5) }); // bytes sintéticos
    }
    return json({ detail: "sin simulación" }, 404);
  });
  return log;
}

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH,
  headless: true,
  args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
});

async function open(viewport, state) {
  const ctx = await browser.newContext({ viewport, permissions: ["microphone"] });
  const page = await ctx.newPage();
  // Se guardan las pistas del micrófono para comprobar que la UI las detiene.
  await page.addInitScript(() => {
    window.__tracks = [];
    const gum = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (c) => {
      const s = await gum(c);
      window.__tracks.push(...s.getTracks());
      return s;
    };
  });
  const log = await mockBackend(page, state);
  await page.goto(`${WEB}/#/tienda/${SLUG}`);
  await page.getByRole("textbox", { name: "Mensaje" }).waitFor();
  return { ctx, page, log };
}
const calls = (log, part) => log.filter((c) => c.path.includes(part));
const tts = (log) => log.filter((c) => c.path.endsWith("/audio") && c.path.includes("/messages/"));
const shot = async (page, name) => SHOTS && page.screenshot({ path: join(SHOTS, name), fullPage: false });
const tracksEnded = (page) => page.evaluate(() => window.__tracks.length > 0 && window.__tracks.every((t) => t.readyState === "ended"));
const until = async (fn, ms = 5000) => {
  const t0 = Date.now();
  while (!(await fn()) && Date.now() - t0 < ms) await new Promise((r) => setTimeout(r, 50));
};

try {
  // --- Escritorio: grabar → Enviar audio → texto al chat → respuesta con audio automático -------
  {
    const state = { enabled: true, ttsFail: false, heard: HEARD, chatDelay: 600 };
    const { ctx, page, log } = await open({ width: 1280, height: 860 }, state);
    const mine = page.locator('audio[aria-label="Tu audio"]');
    const replies = page.locator('audio[aria-label="Respuesta en audio"]');
    const record = page.getByRole("button", { name: "Mandar audio" });
    await record.waitFor();
    check("controles de audio visibles con audio habilitado", await page.getByRole("button", { name: "Adjuntar" }).isVisible());
    check("sin botones de revisión", await page.getByRole("button", { name: /Transcribir|Reemplazar|Agregar al final/ }).count() === 0);

    await record.click();
    await page.getByText("Grabando").waitFor();
    await page.waitForTimeout(1200);
    check("grabando: sin red de voz ni chat antes de Enviar audio",
      calls(log, "/transcriptions").length === 0 && calls(log, "/chat").length === 0);
    await shot(page, "audio-desktop-grabando.png");
    await page.getByRole("button", { name: "Enviar audio" }).click();
    await page.getByText("Escribiendo…").waitFor();
    check("mientras se envía, audio deshabilitado", await record.isDisabled() && await page.getByRole("button", { name: "Adjuntar" }).isDisabled());
    check("pistas del micrófono detenidas al enviar", await tracksEnded(page));
    const stt = calls(log, "/transcriptions");
    check("una sola transcripción, sin conversación todavía", stt.length === 1 && stt[0].search === "" && !stt[0].headers["x-conversation-token"]);
    check("STT recibe WAV PCM mono 16 kHz 16 bits", isBackendWav(stt[0]), JSON.stringify(wavInfo(stt[0].body)));
    const chat = calls(log, "/chat");
    check("la transcripción dispara exactamente un mensaje de chat con ese texto",
      chat.length === 1 && JSON.parse(chat[0].body.toString()).message === HEARD);

    await replies.first().waitFor();
    await page.waitForTimeout(300);
    const note = page.locator(".bubble.me.voice-note");
    check("burbuja de nota de voz con reproductor y texto entendido",
      await note.count() === 1 && await note.locator('audio[aria-label="Tu audio"]').count() === 1
      && (await note.innerText()).includes(`«${HEARD}»`));
    check("tras responder se relee el historial (ids del servidor)", calls(log, `/conversations/${CONV}`).length >= 1);
    const t1 = tts(log);
    check("TTS automático de la respuesta, una vez, por id con token", t1.length === 1
      && t1[0].path.endsWith(`/messages/${botId(1)}/audio`) && t1[0].headers["x-conversation-token"] === TOKEN
      && !t1[0].search && !t1[0].body?.length, t1.map((c) => c.path).join(","));
    check("reproductor de la respuesta con autoplay", await replies.first().evaluate((a) => a.autoplay));
    await shot(page, "audio-desktop-respuesta.png");

    // Adjuntar un archivo con la conversación ya creada: viaja con conversation_id y token.
    await page.locator('input[type=file][accept="audio/*"]').setInputFiles({ name: "consulta.wav", mimeType: "audio/wav", buffer: sineWav(1) });
    await until(async () => (await replies.count()) === 2);
    const stt2 = calls(log, "/transcriptions")[1];
    check("adjunto: STT con conversation_id y token", stt2?.search === `?conversation_id=${CONV}` && stt2.headers["x-conversation-token"] === TOKEN);
    check("adjunto: WAV backend de 1 s ≈ 32 kB", isBackendWav(stt2) && Math.abs(stt2.body.length - 44 - 32000) <= 64, `${stt2?.body.length} bytes`);
    check("adjunto: un chat más y TTS automático de la nueva respuesta",
      calls(log, "/chat").length === 2 && tts(log).length === 2 && tts(log)[1].path.endsWith(`/messages/${botId(3)}/audio`));
    check("cada nota de voz conserva su propio audio", await mine.count() === 2
      && new Set(await mine.evaluateAll((as) => as.map((a) => a.src))).size === 2);

    // Mensaje escrito: no hay TTS automático; «Escuchar» lo pide a mano y sin autoplay.
    await page.getByRole("textbox", { name: "Mensaje" }).fill("Hola");
    await page.getByRole("button", { name: "Enviar", exact: true }).click();
    const listen = page.getByRole("button", { name: "Escuchar" });
    await listen.waitFor();
    await page.waitForTimeout(500);
    check("escrito: sin TTS automático", tts(log).length === 2);
    check("escrito: burbuja de texto sin reproductor", await mine.count() === 2);
    await listen.click();
    await until(async () => (await replies.count()) === 3);
    const t3 = tts(log);
    check("Escuchar pide TTS del mensaje escrito con token", t3.length === 3
      && t3[2].path.endsWith(`/messages/${botId(5)}/audio`) && t3[2].headers["x-conversation-token"] === TOKEN);
    check("Escuchar: reproductor sin autoplay", await replies.nth(2).evaluate((a) => !a.autoplay));

    // Cancelar durante la grabación: no manda nada y libera el micrófono.
    const before = log.length;
    await record.click();
    await page.getByText("Grabando").waitFor();
    await page.waitForTimeout(600);
    await page.getByRole("button", { name: "Cancelar" }).click();
    await page.waitForTimeout(800);
    check("cancelar detiene las pistas", await tracksEnded(page));
    check("cancelar no envía nada", log.slice(before).filter((c) => c.method !== "GET").length === 0 && await mine.count() === 2);

    // Transcripción vacía: error, sin mensaje.
    state.heard = "   ";
    await page.locator('input[type=file][accept="audio/*"]').setInputFiles({ name: "silencio.wav", mimeType: "audio/wav", buffer: sineWav(1) });
    await page.getByRole("alert").filter({ hasText: "No se entendió" }).waitFor();
    check("transcripción vacía: error y nada enviado", calls(log, "/chat").length === 3 && await mine.count() === 2);
    await ctx.close();
  }

  // --- Fallo TTS automático: se muestra una vez, sin reintento ---------------------------------
  {
    const state = { enabled: true, ttsFail: true, heard: HEARD };
    const { ctx, page, log } = await open({ width: 1280, height: 860 }, state);
    await page.locator('input[type=file][accept="audio/*"]').setInputFiles({ name: "consulta.wav", mimeType: "audio/wav", buffer: sineWav(1) });
    await page.getByRole("alert").filter({ hasText: "proveedor de voz" }).waitFor();
    await page.waitForTimeout(1500);
    check("fallo TTS explicado una sola vez", await page.getByRole("alert").filter({ hasText: "proveedor de voz" }).count() === 1);
    check("fallo TTS sin reintento automático", tts(log).length === 1);
    check("fallo TTS conserva la respuesta escrita", await page.getByText(REPLY).isVisible());
    await ctx.close();
  }

  // --- Móvil (390 px) ------------------------------------------------------------------------
  {
    const { ctx, page } = await open({ width: 390, height: 844 }, { enabled: true, ttsFail: false, heard: HEARD });
    const noScroll = () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    await page.getByRole("button", { name: "Mandar audio" }).click();
    await page.getByText("Grabando").waitFor();
    check("móvil grabando sin scroll horizontal", await noScroll());
    await page.waitForTimeout(800);
    await page.getByRole("button", { name: "Enviar audio" }).click();
    await page.locator('audio[aria-label="Respuesta en audio"]').waitFor();
    check("móvil con nota de voz y respuesta en audio sin scroll horizontal", await noScroll());
    await shot(page, "audio-mobile-nota.png");
    await ctx.close();
  }

  // --- Audio deshabilitado por el backend ----------------------------------------------------
  {
    const { ctx, page, log } = await open({ width: 1280, height: 860 }, { enabled: false, ttsFail: false, heard: HEARD });
    await page.getByRole("textbox", { name: "Mensaje" }).fill("Hola");
    await page.getByRole("button", { name: "Enviar", exact: true }).click();
    await page.getByText(REPLY).waitFor();
    await page.waitForTimeout(300);
    check("deshabilitado: sin controles de audio", await page.getByRole("button", { name: /Mandar audio|Adjuntar|Escuchar/ }).count() === 0
      && await page.locator('input[type=file][accept="audio/*"]').count() === 0);
    check("deshabilitado: sin llamadas de voz", calls(log, "/transcriptions").length + tts(log).length === 0);
    await ctx.close();
  }
} catch (e) {
  failures++;
  console.log(`FAIL excepción — ${e.message.split("\n")[0]}`);
} finally {
  await browser.close();
}
console.log(failures ? `${passes} PASS, ${failures} fallas` : `OK — ${passes} PASS`);
process.exit(failures ? 1 : 0);
