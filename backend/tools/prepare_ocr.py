"""Verifica el OCR local: modelos con el hash esperado y una lectura real sin red.

    cd backend && python -m tools.prepare_ocr
"""
from __future__ import annotations

import io
import time
from importlib.metadata import version

from PIL import Image, ImageDraw, ImageFont

from app.documents import ocr


def main() -> None:
    for pkg in ("rapidocr", "onnxruntime", "opencv-python-headless", "pypdfium2", "Pillow"):
        print(f"{pkg}=={version(pkg)}")
    print("modelos verificados en", ocr.verify_models())
    img = Image.new("RGB", (700, 160), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=28)   # incluida en Pillow; sólo ASCII
    draw.text((30, 30), "Importe: $ 1.234,50", fill="black", font=font)
    draw.text((30, 90), "Operacion: 5566778899", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    start = time.perf_counter()
    result = ocr.read_document(buf.getvalue())
    fields = {k: f["value"] for k, f in result["fields"].items()}
    print(f"lectura sin red en {time.perf_counter() - start:.1f} s:", fields)
    assert fields["amount"] == "1234.50" and fields["reference"] == "5566778899", fields


if __name__ == "__main__":
    main()
