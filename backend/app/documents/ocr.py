"""Lectura local de comprobantes (JPG/PNG/PDF): texto, campos sugeridos y confianza.

SÓLO extrae información para que una persona revise. Nada de lo que diga el archivo («pagado»,
«aprobado») ni una confianza alta acredita un pago: eso lo hacen el proveedor o el dueño.

El OCR corre en un subproceso (`python -m app.documents.ocr`, bytes por stdin, JSON por stdout)
sin red, con tiempo máximo y de a uno: un archivo hostil (bomba de píxeles, PDF que cuelga) no
tumba el proceso que lo llama. Motor: RapidOCR + ONNX Runtime en CPU con los modelos PP-OCRv6
small multilingües incluidos en el wheel fijado, verificados por SHA256 antes de usarlos.
Preparación y verificación: backend/tools/README.md.
"""
from __future__ import annotations

import functools
import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

# Límites de la demo.
MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 5
MAX_PIXELS = 20_000_000          # por imagen o página renderizada
TIMEOUT_S = 60.0
PDF_DPI = 200
MIN_PDF_TEXT = 20                 # caracteres para usar el texto del PDF sin OCR
REVIEW_SCORE = 0.90
MAX_AMOUNT_DIGITS = 12            # parte entera; más dígitos => importe sólo para revisión

ENGINE = "rapidocr 3.10.0 / onnxruntime CPU / PP-OCRv6 small multi (det+rec), sin clasificador"
# Mismos SHA256 que publica rapidocr 3.10.0 en default_models.yaml.
MODELS = {
    "Det": ("PP-OCRv6_det_small.onnx", "090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f"),
    "Rec": ("PP-OCRv6_rec_small.onnx", "6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884"),
}

_SLOT = threading.BoundedSemaphore(1)   # un OCR a la vez por proceso


class DocumentRejected(ValueError):
    """Archivo no admitido (tipo, tamaño, páginas, píxeles, cifrado o dañado). No reintentar."""


class OcrFailed(RuntimeError):
    """El lector no terminó (tiempo agotado o fallo interno). Reintentable."""


def sniff(data: bytes) -> str:
    """Tipo real por firma, no por nombre ni Content-Type."""
    if len(data) > MAX_BYTES:
        raise DocumentRejected(f"archivo mayor a {MAX_BYTES // (1024 * 1024)} MiB")
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"%PDF-"):
        return "pdf"
    raise DocumentRejected("tipo no admitido (sólo JPG, PNG o PDF)")


@functools.cache
def isolation() -> list[str]:
    """Prefijo que deja al lector sin red a nivel del sistema operativo (sandbox de macOS o
    namespace de red de Linux). [] si este sistema no lo ofrece: queda sólo el bloqueo de Python."""
    if sys.platform == "darwin":
        prefix = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    elif sys.platform.startswith("linux") and shutil.which("unshare"):
        prefix = ["unshare", "--user", "--map-root-user", "--net"]
    else:
        return []
    try:   # el SO puede no permitirlo (p. ej. contenedor sin user namespaces)
        ok = subprocess.run([*prefix, sys.executable, "-c", ""], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    return prefix if ok else []


def read_document(data: bytes, timeout: float = TIMEOUT_S) -> dict[str, Any]:
    """Lee el comprobante. Devuelve {kind, pages, lines, fields, needs_review, engine}.

    `timeout` es el plazo total (espera de turno incluida), con máximo TIMEOUT_S."""
    kind = sniff(data)
    prefix = isolation()
    timeout = min(timeout, TIMEOUT_S)
    deadline = time.monotonic() + timeout
    if not _SLOT.acquire(timeout=timeout):
        raise OcrFailed(f"tiempo agotado esperando turno ({timeout:g} s)")
    try:
        proc = subprocess.run([*prefix, sys.executable, "-m", "app.documents.ocr"], input=data,
                              capture_output=True, timeout=max(deadline - time.monotonic(), 0.01),
                              cwd=Path(__file__).resolve().parents[2])
    except subprocess.TimeoutExpired:
        raise OcrFailed(f"tiempo agotado ({timeout:g} s)") from None
    finally:
        _SLOT.release()
    if proc.returncode != 0:
        # stderr puede traer texto del documento: no se propaga a logs.
        raise OcrFailed(f"el lector terminó con código {proc.returncode}")
    out = json.loads(proc.stdout)
    if "rejected" in out:
        raise DocumentRejected(out["rejected"])
    network = "red bloqueada por el SO" if prefix else "red bloqueada sólo en Python"
    return {"kind": kind, **out, **suggest_fields(out["lines"]), "engine": f"{ENGINE}; {network}"}


# --- Campos sugeridos ---------------------------------------------------------
# Importe argentino: $ 12.345,67 / ARS 1.000 / U$S 50,00. No toma 1,234.56 (formato US).
_MONEY = re.compile(r"(U\$S|US\$|USD|u\$s|ARS|\$)\s?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?(?!\d|[.,]\d)")
_AMOUNT_LABEL = re.compile(r"import|monto|total|transferiste|pagaste|enviaste|valor", re.I)
_DATE_NUM = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})")
_MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_DATE_TXT = re.compile(r"(?<!\d)(\d{1,2})\s+(?:de\s+)?([a-záéíóú]{3,10})\.?\s+(?:de\s+)?(\d{4})", re.I)
_REF_LABEL = r"(?:operaci[oó]n|transacci[oó]n|comprobante|referencia|identificaci[oó]n|coelsa\s*id|\bid)\b"
_REF_TOKEN = r"(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{5,}"     # >= 6 caracteres con algún dígito
_REF = re.compile(_REF_LABEL + r"[^:#\dA-Z]{0,12}[:#]?\s*(" + _REF_TOKEN + r")\b", re.I)
_REF_ALONE = re.compile(_REF_LABEL + r"\W*$", re.I)       # etiqueta sola: el número va abajo
_CURRENCY = {"$": "ARS", "ARS": "ARS"}


def _pick(cands: list[tuple[Any, float]]) -> dict[str, Any]:
    """Un único valor distinto y legible => sugerido; ninguno, varios o con puntaje bajo => null,
    candidatos y revisión (un valor mal leído no queda precargado)."""
    values = list(dict.fromkeys(v for v, _ in cands))
    if len(values) != 1 or min(s for _, s in cands) < REVIEW_SCORE:
        return {"value": None, "score": None, "candidates": [str(v) for v in values]}
    return {"value": str(values[0]), "score": round(min(s for _, s in cands), 3), "candidates": []}


def _with_next(lines: list[dict[str, Any]], label: re.Pattern) -> list[tuple[str, float]]:
    """Líneas con la etiqueta, más la siguiente (diseños «Importe» / «$ 1.000» en dos renglones)."""
    picked = []
    for i, ln in enumerate(lines):
        if label.search(ln["text"]):
            picked.append((ln["text"], ln["score"]))
            if i + 1 < len(lines) and lines[i + 1]["page"] == ln["page"]:
                picked.append((lines[i + 1]["text"], lines[i + 1]["score"]))
    return picked


def _money(text: str) -> list[tuple[Decimal | str, str]]:
    """Importes del texto; uno fuera de rango queda como texto crudo (nunca se sugiere)."""
    found = []
    for m in _MONEY.finditer(text):
        digits = m[2].replace(".", "")
        amount = (Decimal(digits + "." + (m[3] or "0")).quantize(Decimal("0.01"))
                  if len(digits) <= MAX_AMOUNT_DIGITS else m[0].strip())
        found.append((amount, _CURRENCY.get(m[1].upper(), "USD")))
    return found


def suggest_fields(lines: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = _with_next(lines, _AMOUNT_LABEL)
    pool = labeled if any(_money(t) for t, _ in labeled) else [(ln["text"], ln["score"]) for ln in lines]
    money = [(m, s) for t, s in pool for m in _money(t)]
    amount = _pick([(a, s) for (a, _), s in money])
    if any(isinstance(a, str) for (a, _), _ in money):
        amount = {"value": None, "score": None, "candidates": list(dict.fromkeys(str(a) for (a, _), _ in money))}
    currency = (_pick([(c, s) for (a, c), s in money if str(a) == amount["value"]])
                if amount["value"] else _pick([]))

    dates = []
    for ln in lines:
        found = [(m[1], m[2], m[3]) for m in _DATE_NUM.finditer(ln["text"])]
        found += [(m[1], str(_MONTHS.index(m[2][:3].lower()) + 1), m[3]) for m in _DATE_TXT.finditer(ln["text"])
                  if m[2][:3].lower() in _MONTHS]
        for d, mo, y in found:
            try:
                dates.append((date(int(y) + (2000 if len(y) == 2 else 0), int(mo), int(d)).isoformat(), ln["score"]))
            except ValueError:
                pass
    refs = [(m[1].upper(), ln["score"]) for ln in lines for m in _REF.finditer(ln["text"])]
    refs += [(ln["text"].strip().upper(), ln["score"]) for prev, ln in zip(lines, lines[1:])
             if prev["page"] == ln["page"] and _REF_ALONE.search(prev["text"])
             and re.fullmatch(_REF_TOKEN, ln["text"].strip(), re.I)]
    fields = {"amount": amount, "currency": currency, "date": _pick(dates), "reference": _pick(refs)}
    needs_review = any(f["value"] is None for f in fields.values())
    return {"fields": fields, "needs_review": needs_review}


# --- Subproceso lector --------------------------------------------------------
def verify_models() -> Path:
    """Carpeta de modelos del wheel de rapidocr, con hashes verificados (si no, falla)."""
    import rapidocr
    root = Path(rapidocr.__file__).parent / "models"
    for name, digest in MODELS.values():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"modelo OCR distinto del esperado: {name}")
    return root


def _ocr_lines(engine: Any, image: Any, page: int) -> list[dict[str, Any]]:
    out = engine(image)
    return [{"page": page, "text": t, "score": round(float(s), 3), "source": "ocr"}
            for t, s in zip(out.txts or (), out.scores or ())]


def _read(data: bytes) -> dict[str, Any]:
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS   # Pillow también corta bombas al decodificar
    kind = sniff(data)
    engine = None

    def ocr(image: Any, page: int) -> list[dict[str, Any]]:
        nonlocal engine
        if engine is None:
            from rapidocr import RapidOCR
            root = verify_models()
            engine = RapidOCR(params={"Global.log_level": "error", "Global.use_cls": False,
                                      **{f"{k}.model_path": str(root / n) for k, (n, _) in MODELS.items()}})
        return _ocr_lines(engine, image, page)

    if kind != "pdf":
        import io
        try:
            img = Image.open(io.BytesIO(data))
            # MPO = JPEG multiimagen que generan muchos celulares.
            if img.format not in {"jpeg": ("JPEG", "MPO"), "png": ("PNG",)}[kind]:
                return {"rejected": "el contenido no coincide con el tipo de imagen"}
            if img.width * img.height > MAX_PIXELS:
                return {"rejected": f"imagen de más de {MAX_PIXELS // 1_000_000} MP"}
            img = ImageOps.exif_transpose(img).convert("RGB")
        except (OSError, Image.DecompressionBombError, SyntaxError):
            return {"rejected": "imagen dañada o ilegible"}
        return {"pages": 1, "lines": ocr(img, 1)}

    import pypdfium2 as pdfium
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        # Contraseña de apertura => no se puede leer. Un PDF que sólo restringe permisos sí se lee.
        return {"rejected": "PDF protegido con contraseña" if "password" in str(exc).lower()
                else "PDF dañado o ilegible"}
    if len(pdf) > MAX_PAGES:
        return {"rejected": f"PDF de más de {MAX_PAGES} páginas"}
    lines: list[dict[str, Any]] = []
    for n, page in enumerate(pdf, 1):
        text = page.get_textpage().get_text_bounded()
        if len(text.strip()) >= MIN_PDF_TEXT:
            lines += [{"page": n, "text": t.strip(), "score": 1.0, "source": "pdf_text"}
                      for t in text.splitlines() if t.strip()]
        # Con capa de texto suficiente se usa sólo el texto: hacer OCR además (p. ej. por el logo
        # del banco) suma lecturas ruidosas que vuelven dudoso un dato exacto.
        if len(text.strip()) < MIN_PDF_TEXT:
            w, h = page.get_size()
            if w <= 0 or h <= 0:
                return {"rejected": "PDF dañado o ilegible"}
            # Margen para el redondeo del render; igual se controla el tamaño final.
            scale = min(PDF_DPI / 72, (MAX_PIXELS / ((w + 2) * (h + 2))) ** 0.5)
            img = page.render(scale=scale).to_pil()
            if img.width * img.height > MAX_PIXELS:
                return {"rejected": f"página de más de {MAX_PIXELS // 1_000_000} MP"}
            lines += ocr(img.convert("RGB"), n)
    return {"pages": len(pdf), "lines": lines}


def _main() -> None:
    import socket

    def _offline(*_: Any, **__: Any) -> None:
        raise OSError("el lector OCR no usa la red")
    # Segunda barrera; la garantía la da isolation() cuando el SO la ofrece.
    for name in ("connect", "connect_ex", "sendto", "sendmsg"):
        setattr(socket.socket, name, _offline)
    socket.create_connection = socket.getaddrinfo = _offline
    data = sys.stdin.buffer.read(MAX_BYTES + 1)
    try:
        result = _read(data)
    except DocumentRejected as exc:
        result = {"rejected": str(exc)}
    sys.stdout.write(json.dumps(result))   # ASCII: no depende de la codificación de la consola


if __name__ == "__main__":
    _main()
