import { useRef, useState } from "react";
import { Camera } from "lucide-react";
import type { PhotoCaps } from "../lib/api";

// Tope del archivo original antes de decodificarlo en memoria (lo que viaja es la versión achicada).
const MAX_FILE_BYTES = 25 * 1024 * 1024;
const MAX_SIDE = 1600;
const QUALITY = 0.85;
const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];

// Decodifica la imagen. `createImageBitmap` respeta la orientación EXIF de las fotos del celular;
// si el navegador no lo tiene, se usa un <img> (que también la respeta en los navegadores actuales).
async function decode(file: Blob): Promise<{ src: CanvasImageSource; w: number; h: number; done: () => void }> {
  if (typeof createImageBitmap === "function") {
    try {
      const b = await createImageBitmap(file, { imageOrientation: "from-image" });
      return { src: b, w: b.width, h: b.height, done: () => b.close() };
    } catch {
      /* se prueba con <img> */
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return { src: img, w: img.naturalWidth, h: img.naturalHeight, done: () => URL.revokeObjectURL(url) };
  } catch (e) {
    URL.revokeObjectURL(url);
    throw e;
  }
}

/** Achica la foto en el navegador (lado mayor 1600 px, JPEG 0,85) para ahorrar datos. Si el canvas
 *  falla, devuelve el original cuando el servidor lo acepta tal cual; si no, `null`. */
async function shrink(file: File): Promise<Blob | null> {
  const original = ACCEPTED.includes(file.type) ? file : null;
  let img: Awaited<ReturnType<typeof decode>>;
  try {
    img = await decode(file);
  } catch {
    return original;
  }
  try {
    const scale = Math.min(1, MAX_SIDE / Math.max(img.w, img.h));
    const w = Math.max(1, Math.round(img.w * scale));
    const h = Math.max(1, Math.round(img.h * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return original;
    ctx.fillStyle = "#fff"; // un PNG con transparencia no queda negro al pasar a JPEG
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img.src, 0, 0, w, h);
    const out = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", QUALITY));
    if (!out) return original;
    // Una foto chica ya comprimida puede salir más pesada al recodificarla: se queda la original.
    return original && scale === 1 && original.size <= out.size ? original : out;
  } catch {
    return original;
  } finally {
    img.done();
  }
}

/** Botón de cámara del chat: en el celular abre la cámara, en la compu el selector de archivos.
 *  Prepara la imagen y se la pasa al padre, que la manda a describir y muestra la burbuja. */
export function PhotoInput({ caps, disabled, onPhoto, onError }: {
  caps: PhotoCaps;
  disabled?: boolean;
  /** Recibe la imagen lista para subir (ya achicada). */
  onPhoto: (image: Blob) => void;
  onError: (message: string) => void;
}) {
  const file = useRef<HTMLInputElement>(null);
  const [preparing, setPreparing] = useState(false);

  async function pick(f: File) {
    if (f.size > MAX_FILE_BYTES) return onError("La foto es demasiado pesada. Probá con otra.");
    setPreparing(true);
    try {
      const image = await shrink(f);
      if (!image) return onError("No pude leer esa imagen. Probá con una foto JPG, PNG o WEBP.");
      if (image.size > caps.max_upload_bytes)
        return onError(`La foto pesa más de ${Math.floor(caps.max_upload_bytes / (1024 * 1024)) || 1} MB. Probá con otra.`);
      onPhoto(image);
    } finally {
      setPreparing(false);
    }
  }

  return (
    <>
      <button
        className="btn photo-btn"
        type="button"
        aria-label="Mandar una foto del producto"
        title="Mandar una foto del producto"
        disabled={disabled || preparing}
        onClick={() => file.current?.click()}
      >
        <Camera size={20} aria-hidden="true" />
      </button>
      <input ref={file} type="file" accept={ACCEPTED.join(",")} hidden onChange={(e) => {
        const f = e.target.files?.[0];
        e.target.value = "";
        if (f) void pick(f);
      }} />
    </>
  );
}
