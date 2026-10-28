"""Constancia comercial de compra: una por pedido pagado, emitida en la MISMA transacción que lo
deja PAID (no se pierde ni se duplica aunque fallen los efectos posteriores).

Es una instantánea estable de lo que se compró y de cómo se verificó el pago. No es factura
fiscal ni inventa datos fiscales: sólo usa la identidad del negocio que ya existe.
"""
from __future__ import annotations

import json
from typing import Any, Optional

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
