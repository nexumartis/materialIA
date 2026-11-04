"""Envíos por correo: el negocio despacha por Andreani, OCA, Correo Argentino u otro, carga el número
de seguimiento y el cliente lo recibe en su charla (y el agente lo informa si pregunta).

- Sin integración con el correo: cada correo pide su propio contrato y credenciales por negocio. Hasta
  entonces el número lo carga una persona y nunca se inventa un estado del envío: se informa el número
  y dónde seguirlo.
- El link de seguimiento es la página oficial del correo; si el negocio usa otro, puede cargar su link
  (con «{codigo}» donde va el número).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from . import opportunities, orders, webhooks

# Páginas de seguimiento de cada correo (el cliente pega el número ahí). Sin plantillas con el número:
# los formatos de link de cada correo cambian y no se inventa uno.
CARRIERS: dict[str, dict[str, str]] = {
    "andreani": {"name": "Andreani", "url": "https://www.andreani.com/"},
    "oca": {"name": "OCA", "url": "https://www.oca.com.ar/"},
    "correo_argentino": {"name": "Correo Argentino", "url": "https://www.correoargentino.com.ar/"},
    "otro": {"name": "Otro", "url": ""},
}
SHIPPABLE = ("PAID", "PREPARING")


def tracking_url(carrier: Optional[str], code: Optional[str], custom: Optional[str] = None) -> Optional[str]:
    if custom and code:
        return custom.replace("{codigo}", code)
    return (CARRIERS.get(carrier or "") or {}).get("url") or None


def describe(order: dict[str, Any]) -> Optional[str]:
    """«Salió por Andreani · N° 360002… · seguilo en andreani.com» o None si no se despachó por correo."""
    if not order.get("tracking_code"):
        return None
    name = order.get("carrier_name") or order.get("carrier") or "el correo"
    url = order.get("tracking_url")
    return f"Salió por {name}. Número de seguimiento: {order['tracking_code']}" + (f". Seguilo en {url}" if url else "")


def ship(cur: Any, tenant_id: str, uid: str, order_id: str, body: dict[str, Any],
         custom_url: Optional[str] = None) -> Optional[dict[str, Any]]:
    carrier = body.get("carrier")
    if carrier not in CARRIERS:
        raise ValueError("Elegí el correo.")
    name = " ".join(str(body.get("carrier_name") or "").split())[:40] if carrier == "otro" else CARRIERS[carrier]["name"]
    if carrier == "otro" and not name:
        raise ValueError("Escribí el nombre del correo.")
    code = re.sub(r"\s+", "", str(body.get("tracking_code") or ""))
    if not re.fullmatch(r"[A-Za-z0-9\-]{4,60}", code):
        raise ValueError("El número de seguimiento tiene que tener entre 4 y 60 letras o números.")
    row = orders._fetch(cur, tenant_id, order_id, lock=True)
    if row is None:
        return None
    if row["status"] not in SHIPPABLE or row.get("delivery_method") != "delivery":
        raise ValueError("Sólo se despachan por correo pedidos pagados con envío a domicilio.")
    cur.execute("update orders set carrier = %s, tracking_code = %s, shipped_at = now(), updated_at = now() "
                "where tenant_id = %s and id = %s", (name if carrier == "otro" else carrier, code, tenant_id, order_id))
    orders._advance(cur, tenant_id, order_id, "DISPATCHED")
    url = tracking_url(carrier, code, custom_url)
    if row["conversation_id"]:
        opportunities._add_message(cur, tenant_id, str(row["conversation_id"]), "outbound",
                                   f"¡Tu pedido #{row['number']} salió por {name}! Número de seguimiento: {code}."
                                   + (f" Lo podés seguir en {url}" if url else ""),
                                   {"type": "delivery", "by": None, "tracking": code})
    webhooks.enqueue_order(cur, tenant_id, "order.shipped", order_id, carrier=name, tracking_code=code)
    opportunities._audit(cur, tenant_id, "order_shipped", order_id, {"actor": uid, "carrier": carrier})
    return orders._view(cur, orders._fetch(cur, tenant_id, order_id))
