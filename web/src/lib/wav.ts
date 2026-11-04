// Audio del comprador → el único formato que acepta el backend: WAV PCM mono 16 kHz 16 bits.
// Sin dependencias: decodifica y remuestrea el navegador (decodeAudioData).

export const WAV_RATE = 16000;

/** Muestras [-1, 1] mono → WAV PCM 16 bits little-endian con cabecera de 44 bytes. */
export function encodeWav(samples: Float32Array, rate = WAV_RATE): ArrayBuffer {
  const out = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const ascii = (at: number, s: string) => [...s].forEach((c, i) => out.setUint8(at + i, c.charCodeAt(0)));
  ascii(0, "RIFF");
  out.setUint32(4, 36 + samples.length * 2, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  out.setUint32(16, 16, true); // tamaño del bloque fmt
  out.setUint16(20, 1, true); // PCM
  out.setUint16(22, 1, true); // mono
  out.setUint32(24, rate, true);
  out.setUint32(28, rate * 2, true); // bytes por segundo
  out.setUint16(32, 2, true); // bytes por frame
  out.setUint16(34, 16, true);
  ascii(36, "data");
  out.setUint32(40, samples.length * 2, true);
  samples.forEach((v, i) => {
    const s = Math.max(-1, Math.min(1, v));
    out.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  });
  return out.buffer;
}

/** Grabación o adjunto (cualquier formato que el navegador sepa decodificar) → WAV del backend.
 *  `maxSeconds` recorta (sólo grabaciones, ya cortadas por temporizador); `seconds` es la duración original. */
export async function toWav(blob: Blob, maxSeconds = Infinity): Promise<{ wav: Blob; seconds: number }> {
  // decodeAudioData remuestrea a la frecuencia del contexto; sólo falta mezclar a mono.
  const ctx = new OfflineAudioContext(1, 1, WAV_RATE);
  const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
  const mono = new Float32Array(Math.min(buf.length, maxSeconds * WAV_RATE));
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const ch = buf.getChannelData(c);
    for (let i = 0; i < mono.length; i++) mono[i] += ch[i] / buf.numberOfChannels;
  }
  return { wav: new Blob([encodeWav(mono)], { type: "audio/wav" }), seconds: buf.duration };
}
