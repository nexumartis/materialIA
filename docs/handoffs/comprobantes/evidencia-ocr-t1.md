# Informe del implementador T1 — evidencia sin aprobar

Las afirmaciones siguientes son el informe original de Claude, no un veredicto de revisión. La revisión de Codex detectó bloqueo de red incompleto, timeout parcial y discrepancias de cobertura (dos degradaciones parametrizadas, no cinco). Leer revision-ocr-t1.md antes de reutilizarlo. Las rutas COORD son referencias históricas locales; diseño y fuentes están en esta carpeta. T1 no está integrado.

T1 está terminado: el OCR local funciona de verdad en Windows y sin red, al primer intento, y las 20 pruebas pasan (20 aprobadas, 0 fallidas, 0 salteadas). Corrí la suite tres veces con OCR real, sin mocks: dos con el `conftest` del repo contra la DB local (sólo hace `select 1`) y una sin él. Edición detenida; sin commits, sin tocar DB, remoto ni archivos de N1b.

**Cambio respecto del diseño: el modelo.** El wheel fijado `rapidocr==3.10.0` ya trae los modelos PP-OCRv6 small, que incluyen español, con el mismo SHA256 que publica rapidocr. Por eso no hay que descargar nada: el código fija los hashes y los comprueba en cada lectura. Lee bien `operación`, `Grifería`, `señal` y `$ 12.345,67`.

**Qué cubren las pruebas:**
- **Comprobantes completos:** PNG, JPG, PDF con texto, PDF escaneado y PDF mixto. En todos salen importe, moneda, fecha y referencia correctos.
- **Casos dudosos:** con dos importes distintos, o con la imagen degradada en 5 niveles, nunca inventa un valor: el campo queda vacío y va a revisión.
- **Rechazos:** tipo falso, imagen de más de 20 MP, PDF con contraseña o dañado, más de 5 páginas, más de 10 MiB y tiempo agotado.
- **Sin acción de pago:** que la imagen diga «PAGO APROBADO» no agrega ningún estado de pago al resultado.

Cada lectura tarda unos 3,5 s y ronda 6 s con N1 corriendo en paralelo; un PDF con texto, unos 0,6 s.

**Archivos nuevos o cambiados:**
- `backend/app/documents/ocr.py` (+ `__init__.py`)
- `backend/tools/prepare_ocr.py` y `backend/tools/README.md`
- `backend/tests/test_document_ocr.py`
- `backend/pyproject.toml` (dependencias OCR/PDF; `reportlab` sólo para tests)

`.gitignore` no necesitó cambios porque no se genera nada en el repo. Las dependencias están instaladas sólo en `COORD/ocr-env`.

**Para revisar:**
- Un PDF que sólo restringe permisos (sin contraseña de apertura) se lee; lo dejé así porque es común en bancos.
- Sólo probé comprobantes sintéticos: faltan comprobantes reales de bancos argentinos, fotos torcidas e importes sin `$` (estos últimos quedan vacíos y van a revisión).
- Agregar las dependencias de OCR suma unos 100 MB al entorno del socio.
- T2 tiene que esperar a que N1b cierre `payments/service.py`.
- `OCR-BUILDER.md` en COORD quedó sobrescrito con el resumen corto, así que el diseño detallado para T2–T4 se perdió de ahí. Lo restauré en `OCR-BUILDER-detalle.md`.

Todo está en COORD: el informe en `OCR-T1.md`, el avance en `AVANCE-OCR.md` y los logs en `ocr-logs/`.
