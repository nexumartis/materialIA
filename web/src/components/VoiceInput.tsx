import { useEffect, useRef, useState } from "react";
import { Mic, Paperclip, Send } from "lucide-react";
import { ApiError, type AudioCaps } from "../lib/api";
import { toWav } from "../lib/wav";

// Tope del archivo original antes de decodificarlo en memoria (lo que viaja es el WAV, más chico).
const MAX_FILE_BYTES = 25 * 1024 * 1024;

type Phase = "idle" | "asking" | "recording" | "sending";

const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** Nota de voz estilo WhatsApp: grabar (o adjuntar) → «Enviar audio» → se transcribe y se manda
 *  sola al chat. El comprador ve en su burbuja lo que se entendió. */
export function VoiceInput({ caps, transcribe, maxLength, disabled, onVoice }: {
  caps: AudioCaps;
  transcribe: (wav: Blob, signal: AbortSignal) => Promise<{ text: string }>;
  maxLength: number;
  disabled?: boolean;
  /** Recibe el texto entendido y la URL local del audio (pasa a ser del padre, que la libera). */
  onVoice: (text: string, audioUrl: string) => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timers = useRef<number[]>([]);
  const abort = useRef<AbortController | null>(null);
  const file = useRef<HTMLInputElement>(null);
  // Cada acción nueva, cancelar o desmontar invalida lo que llegue tarde (permiso, decodificación, red).
  const job = useRef(0);
  const cancelled = useRef(false);
  // La entrega termina varios renders después del clic: usa siempre las props vigentes
  // (conversación y lista de mensajes actuales), no las del momento en que se empezó a grabar.
  const latest = useRef({ transcribe, onVoice });
  latest.current = { transcribe, onVoice };

  function stopCapture() {
    timers.current.forEach((t) => window.clearTimeout(t)); // timeouts e intervals comparten ids
    timers.current = [];
    const r = rec.current;
    rec.current = null;
    if (r && r.state !== "inactive") r.stop();
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }

  function reset() {
    job.current++;
    abort.current?.abort();
    abort.current = null;
    stopCapture();
    setElapsed(0);
    setPhase("idle");
  }

  useEffect(
    () => () => {
      job.current++;
      abort.current?.abort();
      stopCapture();
    },
    [],
  );

  async function record() {
    reset();
    setError(null);
    cancelled.current = false;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Este navegador no permite grabar audio. Podés adjuntar un archivo.");
      return;
    }
    const j = job.current;
    setPhase("asking");
    let s: MediaStream;
    try {
      s = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      if (j !== job.current) return;
      setPhase("idle");
      setError((e as DOMException)?.name === "NotAllowedError"
        ? "No hay permiso para usar el micrófono. Habilitalo en el navegador o adjuntá un archivo."
        : "No pude acceder al micrófono. Podés adjuntar un archivo.");
      return;
    }
    if (j !== job.current) {
      s.getTracks().forEach((t) => t.stop()); // permiso concedido después de cancelar
      return;
    }
    stream.current = s;
    const chunks: Blob[] = [];
    let r: MediaRecorder;
    try {
      r = new MediaRecorder(s);
    } catch {
      stopCapture();
      setPhase("idle");
      setError("Este navegador no permite grabar audio. Podés adjuntar un archivo.");
      return;
    }
    rec.current = r;
    r.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
    r.onstop = () => {
      if (j === job.current && !cancelled.current) void deliver(new Blob(chunks, { type: r.mimeType }), j, true);
    };
    r.start();
    const t0 = Date.now();
    setPhase("recording");
    timers.current = [
      window.setInterval(() => setElapsed((Date.now() - t0) / 1000), 250),
      window.setTimeout(stopCapture, caps.max_duration_seconds * 1000), // al tope se envía solo
    ];
  }

  function cancel() {
    cancelled.current = true;
    reset();
  }

  function attach(f: File) {
    reset();
    setError(null);
    void deliver(f, job.current, false);
  }

  async function deliver(blob: Blob, j: number, recorded: boolean) {
    setPhase("sending");
    const fail = (msg: string) => {
      if (j !== job.current) return;
      setPhase("idle");
      setError(msg);
    };
    if (blob.size > MAX_FILE_BYTES) return fail("El archivo es demasiado grande. Probá con un audio más corto.");
    let out: { wav: Blob; seconds: number };
    try {
      // La grabación ya la cortó el temporizador: sólo se recortan los milisegundos de más.
      out = await toWav(blob, recorded ? caps.max_duration_seconds : Infinity);
    } catch {
      return fail("No pude leer ese audio. Probá con otro archivo (MP3, M4A, OGG o WAV).");
    }
    if (j !== job.current) return;
    if (!recorded && out.seconds > caps.max_duration_seconds)
      return fail(`El audio dura ${clock(out.seconds)} y el máximo es ${clock(caps.max_duration_seconds)}.`);
    if (out.wav.size <= 44) return fail("El audio está vacío.");
    if (out.wav.size > caps.max_upload_bytes) return fail("El audio es demasiado largo.");
    const ac = new AbortController();
    abort.current = ac;
    try {
      const text = (await latest.current.transcribe(out.wav, ac.signal)).text.trim();
      if (j !== job.current) return;
      if (!text) return fail("No se entendió ninguna palabra en el audio. Probá grabarlo de nuevo.");
      if (text.length > maxLength) return fail("El audio es demasiado largo. Probá con uno más corto.");
      setPhase("idle");
      latest.current.onVoice(text, URL.createObjectURL(out.wav));
    } catch (e) {
      fail(e instanceof ApiError ? e.message : "No pude enviar el audio. Probá de nuevo.");
    } finally {
      if (abort.current === ac) abort.current = null;
    }
  }

  return (
    <div className="voice">
      {phase === "idle" && (
        <div className="voice-row">
          <button className="btn sm" type="button" disabled={disabled} onClick={() => void record()}>
            <Mic size={14} aria-hidden="true" /> Mandar audio
          </button>
          <button className="btn sm ghost" type="button" disabled={disabled} onClick={() => file.current?.click()}>
            <Paperclip size={14} aria-hidden="true" /> Adjuntar
          </button>
          <input ref={file} type="file" accept="audio/*" hidden onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (f) attach(f);
          }} />
        </div>
      )}
      {phase !== "idle" && (
        <div className="voice-row" role="status">
          <span className="small">
            {phase === "asking" && "Esperando permiso del micrófono…"}
            {phase === "recording" && <><span className="rec-dot" aria-hidden="true" /> Grabando {clock(elapsed)} de {clock(caps.max_duration_seconds)}</>}
            {phase === "sending" && "Enviando audio…"}
          </span>
          {phase === "recording" && (
            <button className="btn sm primary" type="button" onClick={stopCapture}>
              <Send size={12} aria-hidden="true" /> Enviar audio
            </button>
          )}
          {phase !== "sending" && <button className="btn sm ghost" type="button" onClick={cancel}>Cancelar</button>}
        </div>
      )}
      {error && <p className="state err small" role="alert">{error}</p>}
    </div>
  );
}
