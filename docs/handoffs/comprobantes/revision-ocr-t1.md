T1 agrega extracción local de texto y campos sugeridos. En las fuentes adjuntas no hay autoridad financiera: «PAGO APROBADO» sigue siendo texto y `needs_review=False` no acredita dinero. Aplico Ponytail full/review exclusivamente a este motor.

**Debe corregirse:**

1. **Los 60 segundos no cubren toda la lectura** (`ocr.py:65–74`). El semáforo espera indefinidamente; dos llamadas simultáneas pueden hacer que la segunda tarde casi 120 segundos. Además, `timeout` permite superar 60. Arreglo mínimo: plazo total desde la entrada, adquisición del semáforo con vencimiento y tiempo restante para el hijo, con máximo de 60. Sin esto, la espera excede lo documentado. La concurrencia sí queda limitada a uno **por proceso**, no globalmente.

2. **El bloqueo de red es incompleto** (`ocr.py:219–224`). Sólo reemplaza `socket.socket.connect`: una conexión mediante `connect_ex`, por ejemplo, conserva otra salida. Esto no demuestra una filtración desde un documento, pero tampoco garantiza el runtime sin red anunciado. Para sostener esa garantía, bloquear la salida del hijo mediante el sistema operativo y verificarla; no requiere otro servicio.

3. **Un importe extremo rompe el procesamiento** (`ocr.py:117–126`). Un PDF digital con `Monto: $ 123456789012345678901234567890,00` alcanza `Decimal.quantize` y excede su precisión predeterminada. La excepción ocurre en el padre, fuera del aislamiento del lector. Limitar los dígitos admitidos y dejar el campo en revisión, con un test del caso; actualmente puede fallar la llamada completa.

4. **La referencia puede cruzar páginas** (`ocr.py:141–142`). «Referencia» al final de una página toma como referencia un número aislado de la siguiente, aunque pertenezca a otro contenido. Agregar igualdad de página, como ya hace `_with_next`, y un test. Dejarlo permite sugerencias falsas con confianza alta.

**Validación y límites:** hay detección por firma y decodificación posterior, límite de bytes, rechazo explícito por dimensiones de imagen, páginas y contraseña de apertura. En PDF, los 20 MP son un cálculo de escala: falta comprobar dimensiones finales, incluido redondeo, y no constituyen un límite de memoria del decodificador. No aparecen temporales explícitos; tampoco aislamiento del filesystem.

Los tests positivos de PNG/JPEG/PDF escaneado invocan OCR real; el parser usa líneas construidas y el timeout prueba una guarda. El mixto cubre páginas separadas, no texto e imagen coexistiendo en una página. El informe declara cinco degradaciones; la parametrización adjunta tiene dos.

Los hashes fijan los modelos utilizados, pero no pude verificar wheel, metadatos ni dependencias transitivas; Pillow/OpenCV tienen rangos abiertos. Las ejecuciones y tiempos son evidencia declarada por Claude, no pruebas mías.

**Veredicto: corregir 1–4 antes de aprobar T1.**

No ejecuté comandos ni escribí archivos; faltan estado/invariantes y logs adjuntos para confirmar sus observaciones vigentes. N1 y T2–T4 quedan fuera.