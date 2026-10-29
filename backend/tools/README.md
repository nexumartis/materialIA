# OCR local de comprobantes

`app/documents/ocr.py` lee JPG/PNG/PDF y devuelve líneas, campos sugeridos (importe, moneda,
fecha y referencia), puntajes y `needs_review`. **Sólo extrae datos:** no acredita pagos ni cambia
pedidos, aunque el archivo diga «pagado» y el puntaje sea alto.

## Motor

- RapidOCR 3.10.0 + ONNX Runtime 1.31.0 en CPU (fijados en `pyproject.toml`).
- Modelos PP-OCRv6 small multilingües (incluyen español): detección y reconocimiento, **sin**
  clasificador de orientación. Vienen dentro del wheel de rapidocr; no se descarga nada.
  `ocr.MODELS` fija sus SHA256, los mismos que publica rapidocr en `default_models.yaml`. Si un
  archivo no coincide, el lector falla.
- Cada lectura corre en un subproceso, con tiempo máximo y de a uno por proceso. La red del
  subproceso la bloquea el **sistema operativo**: `sandbox-exec` en macOS y `unshare --net` en
  Linux (si el SO lo permite). En Windows, o si eso no está disponible, queda sólo el bloqueo
  de Python, que no es una garantía del SO; el campo `engine` del resultado dice cuál se usó.
  Una página de PDF con capa de texto se lee sólo por su texto (sin OCR); se renderizan y leen con
  OCR sólo las páginas sin texto (escaneadas).
- Windows necesita Microsoft Visual C++ Redistributable 2015+ x64, que pide onnxruntime.

## Límites de la demo

10 MiB por archivo · tipo por firma (JPG, PNG o PDF) · hasta 5 páginas · 20 MP por imagen o página
renderizada (200 dpi como máximo; también se controla el tamaño final) · 60 s por lectura **en
total**, contando la espera del turno · un OCR a la vez por proceso (no global). Se rechazan
los PDF con contraseña de apertura y los archivos dañados. Un PDF que sólo restringe permisos se lee.
Un campo con 0 o varios valores distintos, o con puntaje menor que 0,90, queda en `null` con sus
candidatos y va a revisión: un valor mal leído nunca queda precargado. Un importe con más de
12 dígitos enteros sólo aparece como candidato.

Sin cubrir todavía: memoria del decodificador de imágenes embebidas en un PDF, aislamiento del
filesystem, el contenido de una imagen pegada en una página que además tiene texto (no se lee: si
faltan datos, el comprobante va a revisión) y comprobantes reales de bancos argentinos.

## Preparar y verificar

```bash
cd backend
pip install -e ".[dev]"
python -m tools.prepare_ocr                          # versiones, hashes y una lectura real sin red
python -m pytest -q tests/test_document_ocr.py      # comprobantes sintéticos, OCR real
```

Al igual que el resto de la suite, los tests se saltean si Postgres no responde (`conftest.py`).
Para correr sólo OCR sin base: `python -m pytest --noconftest tests/test_document_ocr.py`.
