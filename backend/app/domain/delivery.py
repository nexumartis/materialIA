"""Entrega del pedido: envío a domicilio o retiro en el local, antes de confirmar la compra.

- **Opciones:** retiro si el negocio cargó la dirección del local (`policies.pickup_address`); envío
  si cargó zonas (`policies.delivery_zones`). Sin ninguna de las dos, no se pregunta nada (como antes).
- **Envío:** la dirección se normaliza con Georef (calle, altura, localidad oficiales); la zona se
  decide con esa localidad/partido; el costo es el que el negocio cargó para la zona. Sin costo
  cargado, el envío queda «a coordinar» y no se cobra: nunca se inventa un precio.
- Se pide nombre y teléfono para coordinar la entrega (sólo para eso: viajan al pedido, no al CRM).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from . import georef
from .inventory import normalize

log = logging.getLogger(__name__)

_PHONE = re.compile(r"(?:\+?54\s?9?\s?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}")


def options(profile: dict[str, Any]) -> dict[str, Any]:
    p = profile.get("policies") or {}
    return {"pickup": (p.get("pickup_address") or "").strip() or None, "zones": p.get("delivery_zones") or [],
            "costs": p.get("shipping_costs") or {}, "hours": (profile.get("hours") or "").strip() or None,
            "courier_zones": p.get("courier_zones") or [], "courier_eta": p.get("courier_eta") or None}


def enabled(profile: dict[str, Any]) -> bool:
    o = options(profile)
    return bool(o["pickup"] or o["zones"])


# --- Dirección ----------------------------------------------------------------------------
def _georef_address(street: str, place: Optional[str]) -> Optional[dict[str, Any]]:
    return georef.address(street, place)


def parse_address(text: str) -> Optional[dict[str, Any]]:
    """«Av. Mitre 1234, Avellaneda» -> dirección normalizada con Georef, o None si no se encontró.
    Necesita calle con número; la localidad ayuda a desambiguar."""
    raw = (text or "").strip()
    if not re.search(r"[a-záéíóúñ]{3,}.*\d{1,5}", raw, re.I):
        return None
    street, _, place = raw.partition(",")
    return _georef_address(street.strip()[:120], place.strip()[:80] or None)


def zone_for(address: dict[str, Any], zones: list[str]) -> Optional[str]:
    """Zona del negocio que cubre la dirección (por localidad, partido, provincia o zona del GBA)."""
    names = georef.names_for({"localidad": address["localidad"], "municipio": address["departamento"],
                              "departamento": address["departamento"], "provincia": address["provincia"]})
    norm = {normalize(z): z for z in zones}
    # «Todo el país» / «Resto del país»: cubre lo que no cae en otra zona (típico del envío por correo).
    rest = next((z for n, z in norm.items() if n in ("todo el pais", "resto del pais", "interior", "argentina")), None)
    return next((norm[n] for n in names if n in norm), rest)


def parse_contact(text: str) -> Optional[dict[str, str]]:
    m = _PHONE.search(text or "")
    if not m or len(re.sub(r"\D", "", m.group(0))) < 8:
        return None
    name = re.sub(r"[,;:-]+", " ", (text[:m.start()] + " " + text[m.end():])).strip()
    name = re.sub(r"(?i)\b(a nombre de|mi nombre es|soy|tel[eé]fono|cel(ular)?|whatsapp)\b", "", name).strip(" .")
    return {"name": name[:80] or "", "phone": re.sub(r"[^\d+]", "", m.group(0))[:20]}


# --- Pedido -------------------------------------------------------------------------------
def apply(cur: Any, tenant_id: str, order_id: str, method: str, *, address: Optional[dict[str, Any]] = None,
          contact: Optional[dict[str, str]] = None, cost: Optional[float] = None, note: Optional[str] = None) -> None:
    """Guarda la entrega en el carrito/pedido y recalcula el total con el envío (0 si es retiro o a
    coordinar)."""
    from . import orders
    cur.execute("update orders set delivery_method = %s, delivery_address = %s::jsonb, delivery_contact = %s::jsonb, "
                "delivery_note = %s, shipping = %s, updated_at = now() where tenant_id = %s and id = %s",
                (method, json.dumps(address, ensure_ascii=False) if address else None,
                 json.dumps(contact, ensure_ascii=False) if contact else None, (note or None) and note[:300],
                 round(float(cost or 0), 2), tenant_id, order_id))
    orders._recompute(cur, tenant_id, order_id)


def describe(order: dict[str, Any]) -> Optional[str]:
    """Una línea para el resumen, la bandeja y la constancia."""
    m = order.get("delivery_method")
    if m == "pickup":
        return "Retiro en el local"
    if m == "delivery":
        a = order.get("delivery_address") or {}
        place = a.get("texto") or ", ".join(x for x in (f"{a.get('calle', '')} {a.get('altura', '')}".strip(),
                                                         a.get("localidad")) if x)
        note = f" ({order['delivery_note']})" if order.get("delivery_note") else ""
        from .reparto import describe_slot
        when = describe_slot(order)
        return f"Envío a {place}{note}" + (f" · {when}" if when else "")
    return None
