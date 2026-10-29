"""Constancia comercial de compra: una por pedido pagado, emitida en la MISMA transacción que lo
deja PAID (no se pierde ni se duplica aunque fallen los efectos posteriores).

Es una instantánea estable de lo que se compró y de cómo se verificó el pago. No es factura
fiscal ni inventa datos fiscales: sólo usa la identidad del negocio que ya existe.
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from . import orders

LEGEND = "Constancia comercial de compra — no es factura fiscal"
ORIGINS = {
    "mercadopago": "Mercado Pago (verificado con el proveedor)",
    "simulated": "Pago simulado (entorno de prueba)",
    "transfer": "Transferencia verificada por el negocio",
}


def _snapshot(cur: Any, tenant_id: str, order: dict[str, Any], payment: dict[str, Any]) -> dict[str, Any]:
    cur.execute("select name from tenants where id = %s", (tenant_id,))
    business = cur.fetchone()["name"]
    reference = payment["provider_payment_id"] or ""
    if payment["provider"] == "transfer":
        reference = reference.split(":", 1)[-1]   # sin el prefijo interno del negocio
    return {
        "legend": LEGEND,
        "business": business,
        "order_number": order["number"],
        "items": [{k: it[k] for k in ("sku", "name", "qty", "unit_price", "line_total")}
                  for it in orders._items(cur, tenant_id, str(order["id"]))],
        "subtotal": float(order["subtotal"]),
        "shipping": float(order["shipping"]),
        "total": float(order["total"]),
        "currency": order["currency"],
        "paid_at": order["paid_at"].isoformat(),
        "payment": {"origin": ORIGINS[payment["provider"]], "reference": reference,
                    "amount": float(payment["amount"]), "currency": payment["currency"]},
    }


def issue(cur: Any, tenant_id: str, order_id: str, payment_id: str) -> Optional[str]:
    """Emite la constancia del pedido recién pagado. Devuelve su id, o None si ya existía."""
    order = orders._fetch(cur, tenant_id, order_id)
    cur.execute("select provider, provider_payment_id, amount, currency from payments "
                "where tenant_id = %s and id = %s", (tenant_id, payment_id))
    snapshot = _snapshot(cur, tenant_id, order, cur.fetchone())
    cur.execute(
        "insert into receipts (tenant_id, order_id, payment_id, snapshot) values (%s, %s, %s, %s::jsonb) "
        "on conflict (tenant_id, order_id) do nothing returning id",
        (tenant_id, order_id, payment_id, json.dumps(snapshot)),
    )
    row = cur.fetchone()
    return str(row["id"]) if row else None


def get(cur: Any, tenant_id: str, order_id: str) -> Optional[dict[str, Any]]:
    cur.execute("select id, snapshot, issued_at from receipts where tenant_id = %s and order_id = %s",
                (tenant_id, order_id))
    row = cur.fetchone()
    return ({"id": str(row["id"]), "issued_at": row["issued_at"].isoformat(), **row["snapshot"]}
            if row else None)


def in_conversation(cur: Any, tenant_id: str, conversation_id: str, receipt_id: str) -> Optional[dict[str, Any]]:
    """Constancia de un pedido de ESA conversación (el comprador sólo baja las suyas)."""
    cur.execute("select r.order_id from receipts r join orders o on o.tenant_id = r.tenant_id and o.id = r.order_id "
                "where r.tenant_id = %s and r.id = %s and o.conversation_id = %s",
                (tenant_id, receipt_id, conversation_id))
    row = cur.fetchone()
    return get(cur, tenant_id, str(row["order_id"])) if row else None


# --- PDF (a demanda, desde la instantánea) ---------------------------------------
_AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _fonts() -> tuple[str, str]:
    """Vera viene con reportlab: acentos y signos sin depender de las fuentes de la PC."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab
    if "Vera" not in pdfmetrics.getRegisteredFontNames():
        base = Path(reportlab.__file__).parent / "fonts"
        pdfmetrics.registerFont(TTFont("Vera", str(base / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("VeraBd", str(base / "VeraBd.ttf")))
    return "Vera", "VeraBd"


def _amount(value: float, currency: str) -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'U$S' if currency == 'USD' else '$'} {text}"


def _when(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(_AR_TZ).strftime("%d/%m/%Y %H:%M") + " (hora Argentina)"


def render_pdf(receipt: dict[str, Any]) -> bytes:
    """PDF A4 de la constancia. Sólo datos de la instantánea; nada fiscal."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    regular, bold = _fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=1)
    c.setTitle(f"Constancia de compra — pedido #{receipt['order_number']}")
    width, height = A4
    left, right, y = 56, width - 56, height - 64

    def line(text: str, size: float = 10, font: str = regular, x: float = left, step: float = 16) -> None:
        nonlocal y
        if y < 90:   # pedidos largos: página nueva
            c.showPage()
            y = height - 64
        c.setFont(font, size)
        c.drawString(x, y, text)
        y -= step

    line(receipt["business"], 16, bold, step=22)
    line(LEGEND, 11, bold, step=26)
    line(f"Pedido #{receipt['order_number']}", 11, bold)
    line(f"Pagado: {_when(receipt['paid_at'])}")
    line(f"Emitida: {_when(receipt['issued_at'])}", step=24)

    line("Productos", 11, bold)
    for it in receipt["items"]:
        line(f"{it['qty']} × {it['name']}  ({it['sku']})", x=left + 8, step=12)
        c.setFont(regular, 10)
        c.drawRightString(right, y + 12, _amount(it["line_total"], receipt["currency"]))
        line(f"{_amount(it['unit_price'], receipt['currency'])} c/u", 8, x=left + 8, step=16)
    y -= 4
    if receipt["shipping"]:
        line("Envío")
        c.drawRightString(right, y + 16, _amount(receipt["shipping"], receipt["currency"]))
    line(f"Total ({receipt['currency']})", 12, bold, step=26)
    c.setFont(bold, 12)
    c.drawRightString(right, y + 26, _amount(receipt["total"], receipt["currency"]))

    pay = receipt["payment"]
    line("Pago verificado", 11, bold)
    line(f"Origen: {pay['origin']}")
    if pay["reference"]:
        line(f"Referencia: {pay['reference']}")
    line(f"Importe: {_amount(pay['amount'], pay['currency'])} {pay['currency']}", step=28)
    line("Este documento acredita una compra pagada en el negocio. No es una factura ni un comprobante fiscal.",
         8, step=12)
    line(f"Constancia {receipt['id']}", 7)
    c.save()
    return buf.getvalue()
