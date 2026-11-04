// Uso, desde web/: node --test src/lib/wav.test.mjs  (Node ≥ 22.18 importa .ts sin compilar)
import assert from "node:assert/strict";
import test from "node:test";
import { encodeWav } from "./wav.ts";

test("WAV PCM mono 16 kHz 16 bits con la cabecera que valida el backend", () => {
  const v = new DataView(encodeWav(new Float32Array([0, 1, -1, 2, -0.5])));
  const str = (at, n) => String.fromCharCode(...new Uint8Array(v.buffer, at, n));
  assert.equal(v.byteLength, 44 + 5 * 2);
  assert.equal(str(0, 4), "RIFF");
  assert.equal(v.getUint32(4, true), v.byteLength - 8);
  assert.equal(str(8, 4), "WAVE");
  assert.equal(str(12, 4), "fmt ");
  assert.equal(v.getUint16(20, true), 1); // PCM
  assert.equal(v.getUint16(22, true), 1); // mono
  assert.equal(v.getUint32(24, true), 16000);
  assert.equal(v.getUint32(28, true), 32000);
  assert.equal(v.getUint16(32, true), 2);
  assert.equal(v.getUint16(34, true), 16);
  assert.equal(str(36, 4), "data");
  assert.equal(v.getUint32(40, true), 10);
  // 0, máximo, mínimo, recorte de un valor fuera de rango, negativo.
  assert.deepEqual([0, 1, 2, 3, 4].map((i) => v.getInt16(44 + i * 2, true)), [0, 32767, -32768, 32767, -16384]);
});
