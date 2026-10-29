"""OCR real (sin mocks) sobre comprobantes sintéticos generados acá: RapidOCR local, sin red.

Los textos se dibujan con Vera (incluida en reportlab, no depende de las fuentes de la PC).
Ninguna lectura acredita un pago: sólo se comprueban texto, campos sugeridos y rechazos.
"""
from __future__ import annotations

import io
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import reportlab
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import pdfencrypt
from reportlab.pdfgen import canvas

from app.documents import ocr

FONT = ImageFont.truetype(str(Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"), 28)
RECEIPT = ["Comprobante de transferencia", "PAGO APROBADO", "Importe: $ 12.345,67",
           "Fecha: 24/10/2026 14:32", "N° de operación: 98765432101", "Destino: Grifería Demo SRL"]
EXPECTED = {"amount": "12345.67", "currency": "ARS", "date": "2026-10-24", "reference": "98765432101"}


def _image(lines: list[str]) -> Image.Image:
    img = Image.new("RGB", (900, 70 + 60 * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    for i, text in enumerate(lines):
        draw.text((40, 30 + i * 60), text, fill="black", font=FONT)
    return img


def _encode(img: Image.Image, fmt: str, **kw) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **kw)
    return buf.getvalue()


def _text_pdf(pages: list[list[str]], **kw) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, **kw)
    for lines in pages:
        for i, text in enumerate(lines):
            c.drawString(72, 760 - 22 * i, text)
        c.showPage()
    c.save()
    return buf.getvalue()


def _values(result: dict) -> dict:
    return {k: f["value"] for k, f in result["fields"].items()}


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_image_receipt(fmt):
    data = _encode(_image(RECEIPT), fmt, **({"quality": 70} if fmt == "JPEG" else {}))
    result = ocr.read_document(data)
    assert result["kind"] == fmt.lower()
    assert "operación" in " ".join(ln["text"] for ln in result["lines"])
    assert _values(result) == EXPECTED
    assert result["needs_review"] is False
    # «PAGO APROBADO» en la imagen es texto, no un estado: el resultado no tiene nada de pago.
    assert set(result) == {"kind", "pages", "lines", "fields", "needs_review", "engine"}


def test_digital_pdf_uses_text_layer():
    result = ocr.read_document(_text_pdf([RECEIPT]))
    assert {ln["source"] for ln in result["lines"]} == {"pdf_text"}
    assert _values(result) == EXPECTED


def test_scanned_pdf_is_ocrd():
    result = ocr.read_document(_encode(_image(RECEIPT), "PDF", resolution=150))
    assert {ln["source"] for ln in result["lines"]} == {"ocr"}
    assert _values(result) == EXPECTED


def test_mixed_pdf_text_page_and_scanned_page():
    header = _text_pdf([["Banco Demo - Resumen de operaciones del cliente", "Página de cortesía"]])
    scanned = _encode(_image(RECEIPT), "PDF", resolution=150)
    import pypdfium2 as pdfium
    merged = pdfium.PdfDocument.new()
    merged.import_pages(pdfium.PdfDocument(header))
    merged.import_pages(pdfium.PdfDocument(scanned))
    buf = io.BytesIO()
    merged.save(buf)
    result = ocr.read_document(buf.getvalue())
    assert result["pages"] == 2
    assert {(ln["page"], ln["source"]) for ln in result["lines"]} >= {(1, "pdf_text"), (2, "ocr")}
    assert _values(result) == EXPECTED


def test_two_different_amounts_stay_for_review():
    lines = ["Importe: $ 12.345,67", "Total debitado: $ 12.400,00", "Fecha: 24/10/2026",
             "N° de operación: 98765432101"]
    result = ocr.read_document(_encode(_image(lines), "PNG"))
    amount = result["fields"]["amount"]
    assert amount["value"] is None and set(amount["candidates"]) == {"12345.67", "12400.00"}
    assert result["fields"]["currency"]["value"] is None
    assert result["needs_review"] is True


@pytest.mark.parametrize("width, blur", [(300, 1.5), (180, 2)], ids=["parcial", "ilegible"])
def test_degraded_receipt_never_invents_values(width, blur):
    img = _image(RECEIPT)
    img = img.resize((width, img.height * width // img.width)).filter(ImageFilter.GaussianBlur(blur)).resize(img.size)
    result = ocr.read_document(_encode(img, "JPEG", quality=25))
    assert all(v in (None, EXPECTED[k]) for k, v in _values(result).items())
    assert result["fields"]["amount"]["value"] is None
    assert result["needs_review"] is True


@pytest.mark.parametrize("data, reason", [
    (b"GIF89a" + b"\0" * 100, "tipo no admitido"),
    (b"\x89PNG\r\n\x1a\n" + b"basura" * 50, "dañada"),
    (_encode(Image.new("L", (5000, 5000), 255), "PNG"), "MP"),
    (_text_pdf([["x"]], encrypt=pdfencrypt.StandardEncryption("clave", "dueño")), "contraseña"),
    (_text_pdf([RECEIPT])[:300], "dañado"),
    (_text_pdf([["página"]] * (ocr.MAX_PAGES + 1)), "páginas"),
    (b"%PDF-" + b"\0" * ocr.MAX_BYTES, "MiB"),
], ids=["gif", "png-falso", "bomba-25mp", "pdf-contraseña", "pdf-truncado", "pdf-6-paginas", "10mib"])
def test_rejections(data, reason):
    with pytest.raises(ocr.DocumentRejected, match=reason):
        ocr.read_document(data)


def test_timeout_kills_the_reader():
    with pytest.raises(ocr.OcrFailed, match="tiempo"):
        ocr.read_document(_encode(_image(RECEIPT), "PNG"), timeout=0.2)


def test_timeout_includes_waiting_for_the_slot():
    # Otro OCR ocupa el turno: el plazo total vence esperando, sin lanzar el lector.
    assert ocr._SLOT.acquire(timeout=5)
    try:
        start = time.monotonic()
        with pytest.raises(ocr.OcrFailed, match="esperando turno"):
            ocr.read_document(_encode(_image(RECEIPT), "PNG"), timeout=0.3)
        assert time.monotonic() - start < 2
    finally:
        ocr._SLOT.release()


def test_timeout_is_capped(monkeypatch):
    seen = {}

    def fake_run(*_, timeout, **__):
        seen["timeout"] = timeout
        raise subprocess.TimeoutExpired("ocr", timeout)
    monkeypatch.setattr(ocr.subprocess, "run", fake_run)
    monkeypatch.setattr(ocr, "isolation", lambda: [])
    with pytest.raises(ocr.OcrFailed):
        ocr.read_document(_encode(_image(RECEIPT), "PNG"), timeout=600)
    assert seen["timeout"] <= ocr.TIMEOUT_S


def test_reader_has_no_network_at_os_level():
    """Con el aislamiento del SO, ni `connect_ex` (que esquiva el bloqueo de Python) sale."""
    prefix = ocr.isolation()
    if not prefix:
        pytest.skip(f"{sys.platform} no ofrece aislamiento de red del SO; queda sólo el de Python")
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        probe = f"import socket; print(socket.socket().connect_ex(('127.0.0.1', {server.getsockname()[1]})))"
        free = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=30)
        jailed = subprocess.run([*prefix, sys.executable, "-c", probe], capture_output=True, text=True, timeout=30)
    assert free.stdout.strip() == "0"
    assert jailed.stdout.strip() not in ("", "0")


def test_models_match_pinned_hashes():
    root = ocr.verify_models()
    assert all((root / name).is_file() for name, _ in ocr.MODELS.values())


@pytest.mark.parametrize("lines, expected", [
    (["Monto", "U$S 1.250,00", "ID de transacción", "MP-7788990011"],
     {"amount": "1250.00", "currency": "USD", "reference": "MP-7788990011"}),
    (["Total: 1,234.56", "Comprobante de transferencia"], {"amount": None, "reference": None}),
    (["Viernes, 24 de octubre de 2026", "Pagaste $ 980"], {"date": "2026-10-24", "amount": "980.00"}),
])
def test_field_parser(lines, expected):
    fields = ocr.suggest_fields([{"page": 1, "text": t, "score": 0.99} for t in lines])["fields"]
    assert {k: fields[k]["value"] for k in expected} == expected


def test_extreme_amount_goes_to_review_without_crashing():
    result = ocr.read_document(_text_pdf([["Monto: $ 123456789012345678901234567890,00",
                                           "Fecha: 24/10/2026", "N° de operación: 98765432101"]]))
    amount = result["fields"]["amount"]
    assert amount["value"] is None and amount["candidates"] == ["$ 123456789012345678901234567890,00"]
    assert result["needs_review"] is True


def test_reference_label_does_not_take_a_number_from_the_next_page():
    lines = [{"page": 1, "text": "Importe: $ 1.000,00", "score": 0.99},
             {"page": 1, "text": "Referencia", "score": 0.99},
             {"page": 2, "text": "4455667788", "score": 0.99}]
    assert ocr.suggest_fields(lines)["fields"]["reference"]["value"] is None
    lines[2]["page"] = 1
    assert ocr.suggest_fields(lines)["fields"]["reference"]["value"] == "4455667788"


def test_low_score_value_is_a_candidate_not_a_suggestion():
    fields = ocr.suggest_fields([{"page": 1, "text": "N° de operación 98765432105", "score": 0.64}])["fields"]
    assert fields["reference"] == {"value": None, "score": None, "candidates": ["98765432105"]}


def test_text_pdf_with_a_logo_uses_only_its_text():
    """Un PDF de banco con capa de texto y un logo: el OCR del logo no vuelve dudoso un dato exacto."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    logo = io.BytesIO()
    _image(["BANCO DEMO"]).save(logo, "PNG")
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(io.BytesIO(logo.getvalue())), 72, 780, width=200, height=40)
    for i, text in enumerate(RECEIPT):
        c.drawString(72, 740 - 22 * i, text)
    c.save()
    result = ocr.read_document(buf.getvalue())
    assert {ln["source"] for ln in result["lines"]} == {"pdf_text"}
    assert _values(result) == EXPECTED and result["needs_review"] is False
