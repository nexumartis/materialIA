"""Perfil del agente de cada negocio: cómo se presenta, cómo habla y qué afirma de sí mismo
(preguntas frecuentes, reglas, envíos, horarios, medios de pago). Plantillas por rubro.

Las FAQ y reglas son datos que el NEGOCIO afirma: el agente puede repetirlos, pero no inventa
nada que no esté acá, en el catálogo o en los pedidos.
"""
from __future__ import annotations

import json
import re
import secrets
import unicodedata
from typing import Any, Optional

from ..db import system_tx

TONES = ("cercano", "profesional", "formal")

# Plantillas por rubro: punto de partida que el negocio ajusta en el formulario.
TEMPLATES: dict[str, dict[str, Any]] = {
    "sanitarios": {
        "label": "Sanitarios y grifería",
        "seller_name": "Caro",
        "tone": "cercano",
        "greeting": "¡Hola! Soy {seller}, la asistente virtual de {business}. ¿Qué estás buscando? "
                    "Canillas, duchas, sanitarios, repuestos…",
        "faq": [
            {"q": "¿Hacen envíos?", "a": "Completá con tus zonas y costos de envío."},
            {"q": "¿Puedo retirar en el local?", "a": "Completá con la dirección y horarios de retiro."},
            {"q": "¿Las canillas traen flexibles?", "a": "Completá según tus productos."},
        ],
        "rules": ["Si no hay información técnica suficiente sobre una compatibilidad, decilo y "
                  "ofrecé que lo confirme una persona."],
    },
    "ferreteria": {
        "label": "Ferretería",
        "seller_name": "Nico",
        "tone": "cercano",
        "greeting": "¡Hola! Soy {seller}, el asistente virtual de {business}. ¿En qué te ayudo?",
        "faq": [
            {"q": "¿Hacen envíos?", "a": "Completá con tus zonas y costos de envío."},
            {"q": "¿Venden por mayor?", "a": "Completá con tu política de mayoristas."},
        ],
        "rules": [],
    },
    "construccion": {
        "label": "Materiales de construcción",
        "seller_name": "Juli",
        "tone": "profesional",
        "greeting": "¡Hola! Soy {seller}, del equipo de {business}. ¿Qué material necesitás y para qué obra?",
        "faq": [
            {"q": "¿Entregan en obra?", "a": "Completá con zonas, costos y plazos de entrega en obra."},
            {"q": "¿Hacen cómputo de materiales?", "a": "Completá si una persona hace el cómputo."},
        ],
        "rules": ["Los cálculos de cantidades para obra los confirma una persona del equipo."],
    },
    "generico": {
        "label": "Otro rubro",
        "seller_name": "Asistente",
        "tone": "cercano",
        "greeting": "¡Hola! Soy {seller}, el asistente virtual de {business}. ¿En qué te puedo ayudar?",
        "faq": [],
        "rules": [],
    },
}

_FIELDS = ("business_type", "public_slug", "seller_name", "tone", "greeting", "faq", "rules",
           "shipping", "hours", "payment_methods", "policies", "disabled_tools")
_JSON_FIELDS = ("faq", "rules", "policies", "disabled_tools")

# Herramientas que el negocio puede apagar. Buscar, consultar y el carrito son la base del agente.
TOGGLEABLE_TOOLS = {
    "comparar_productos": "Comparar y recomendar entre opciones",
    "preparar_compra": "Vender directo (resumen, confirmación y link de pago)",
    "estado_pedido": "Informar el estado de los pedidos",
    "consultar_envio": "Responder si se envía a una zona",
    "buscar_info_negocio": "Buscar en los documentos del negocio",
    "historial_cliente": "Consultar compras anteriores del cliente",
}

# Políticas: las hace cumplir el CÓDIGO (dominio de pedidos y herramientas), no el modelo.
#   min_order_total        compra mínima para cerrar un pedido (pesos)
#   delivery_zones         zonas a las que se envía (vacío = no se informa por zona)
#   human_only_categories  categorías que sólo vende una persona (no entran al carrito)
POLICY_KEYS = ("min_order_total", "delivery_zones", "shipping_costs", "human_only_categories")


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:40].strip("-") or "negocio"


def template_profile(business_type: str, business_name: str) -> dict[str, Any]:
    t = TEMPLATES.get(business_type) or TEMPLATES["generico"]
    seller = t["seller_name"]
    return {
        "business_type": business_type if business_type in TEMPLATES else "generico",
        "seller_name": seller, "tone": t["tone"],
        "greeting": t["greeting"].format(seller=seller, business=business_name),
        "faq": [dict(x) for x in t["faq"]], "rules": list(t["rules"]),
        "shipping": "", "hours": "", "payment_methods": "",
    }


def _row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in _FIELDS} | {"version": row["version"],
                                            "updated_at": row["updated_at"].isoformat()}


def _get(cur: Any, tenant_id: str) -> Optional[dict[str, Any]]:
    cur.execute(f"select {', '.join(_FIELDS)}, version, updated_at from agent_profiles where tenant_id = %s",
                (tenant_id,))
    row = cur.fetchone()
    return _row(row) if row else None


def _ensure(cur: Any, tenant_id: str, business_name: str) -> dict[str, Any]:
    """Perfil del negocio; si no existe, lo crea con la plantilla genérica y un slug libre."""
    current = _get(cur, tenant_id)
    if current:
        return current
    base = template_profile("generico", business_name)
    slug = f"{slugify(business_name)}-{secrets.token_hex(2)}"
    cur.execute(
        "insert into agent_profiles (tenant_id, business_type, public_slug, seller_name, tone, greeting, faq, rules) "
        "values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb) on conflict (tenant_id) do nothing",
        (tenant_id, base["business_type"], slug, base["seller_name"], base["tone"], base["greeting"],
         json.dumps(base["faq"]), json.dumps(base["rules"])),
    )
    profile = _get(cur, tenant_id)
    _snapshot(cur, tenant_id, profile, None)
    return profile


def validate(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza y valida lo que manda el formulario. ValueError con un mensaje para el usuario."""
    out: dict[str, Any] = {}
    if "business_type" in data:
        if data["business_type"] not in TEMPLATES:
            raise ValueError("Rubro inválido.")
        out["business_type"] = data["business_type"]
    if "public_slug" in data:
        slug = slugify(str(data["public_slug"]))
        if not re.fullmatch(r"[a-z0-9]([a-z0-9-]{1,46}[a-z0-9])", slug):
            raise ValueError("El link debe tener entre 3 y 48 letras, números o guiones.")
        out["public_slug"] = slug
    if "tone" in data:
        if data["tone"] not in TONES:
            raise ValueError("Tono inválido.")
        out["tone"] = data["tone"]
    for key, limit in (("seller_name", 40), ("greeting", 400), ("shipping", 600), ("hours", 300),
                       ("payment_methods", 300)):
        if key in data:
            value = str(data[key] or "").strip()
            if key == "seller_name" and not value:
                raise ValueError("El agente necesita un nombre.")
            out[key] = value[:limit]
    if "faq" in data:
        faq = [{"q": str(x.get("q", "")).strip()[:200], "a": str(x.get("a", "")).strip()[:600]}
               for x in (data["faq"] or []) if isinstance(x, dict)]
        out["faq"] = [x for x in faq if x["q"] and x["a"]][:30]
    if "rules" in data:
        out["rules"] = [str(r).strip()[:300] for r in (data["rules"] or []) if str(r).strip()][:30]
    if "disabled_tools" in data:
        tools = [str(t) for t in (data["disabled_tools"] or [])]
        unknown = [t for t in tools if t not in TOGGLEABLE_TOOLS]
        if unknown:
            raise ValueError(f"Herramienta desconocida: {unknown[0]}.")
        out["disabled_tools"] = sorted(set(tools))
    if "policies" in data:
        out["policies"] = validate_policies(data["policies"] or {})
    return out


def _words(values: Any, limit: int = 40) -> list[str]:
    if isinstance(values, str):
        values = values.split(",")
    return [str(v).strip()[:80] for v in (values or []) if str(v).strip()][:limit]


def validate_policies(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Políticas inválidas.")
    out: dict[str, Any] = {}
    minimum = raw.get("min_order_total")
    if minimum not in (None, ""):
        try:
            minimum = float(minimum)
        except (TypeError, ValueError):
            raise ValueError("La compra mínima debe ser un número.")
        if minimum < 0:
            raise ValueError("La compra mínima no puede ser negativa.")
        if minimum:
            out["min_order_total"] = minimum
    # «CABA: 5000» o «GBA = $8.000»: zona con costo de envío cargado por el negocio (el agente lo
    # informa tal cual; sin costo, sólo dice si se envía).
    zones, costs = [], {}
    raw_zones = raw.get("delivery_zones")
    if isinstance(raw_zones, str):   # «Quilmes: 4.500,50»: la coma de los centavos no separa zonas
        raw_zones = re.split(r",(?!(?<=\d,)\d{1,2}\s*(?:,|$))", raw_zones)
    for entry in _words(raw_zones):
        name, _, cost = entry.replace("=", ":").partition(":")
        name = name.strip()
        if not name:
            continue
        zones.append(name)
        if cost.strip():
            if not re.fullmatch(r"\$?\s*[\d.,]+", cost.strip()):
                raise ValueError(f"El costo de envío de «{name}» debe ser un número.")
            amount = re.sub(r"[^\d,.]", "", cost)
            amount = amount.replace(".", "").replace(",", ".") if "," in amount or re.fullmatch(r"\d{1,3}(\.\d{3})+", amount) else amount
            try:
                value = float(amount)
            except ValueError:
                raise ValueError(f"El costo de envío de «{name}» debe ser un número.")
            if value < 0 or value > 10_000_000:
                raise ValueError(f"El costo de envío de «{name}» no es válido.")
            costs[name] = value
    for name, value in (raw.get("shipping_costs") or {}).items() if isinstance(raw.get("shipping_costs"), dict) else []:
        if name in zones and name not in costs and isinstance(value, (int, float)) and 0 <= value <= 10_000_000:
            costs[name] = float(value)
    if zones:
        out["delivery_zones"] = zones
    if costs:
        out["shipping_costs"] = costs
    cats = [c.lower() for c in _words(raw.get("human_only_categories"))]
    if cats:
        out["human_only_categories"] = cats
    return out


def policies(cur: Any, tenant_id: str) -> dict[str, Any]:
    """Políticas vigentes del negocio (para el dominio de pedidos y las herramientas)."""
    cur.execute("select policies from agent_profiles where tenant_id = %s", (tenant_id,))
    row = cur.fetchone()
    return dict(row["policies"] or {}) if row else {}


def tool_enabled(profile: dict[str, Any], name: str) -> bool:
    return name not in (profile.get("disabled_tools") or [])


# --- Versiones ------------------------------------------------------------------------
_VERSIONED = tuple(f for f in _FIELDS if f != "public_slug")


def _snapshot(cur: Any, tenant_id: str, profile: dict[str, Any], created_by: Optional[str]) -> None:
    cur.execute(
        "insert into agent_profile_versions (tenant_id, version, content, created_by) "
        "values (%s, %s, %s::jsonb, %s) on conflict do nothing",
        (tenant_id, profile["version"], json.dumps({k: profile[k] for k in _VERSIONED}), created_by),
    )


def list_versions(cur: Any, tenant_id: str, limit: int = 30) -> list[dict[str, Any]]:
    cur.execute(
        "select version, content, created_at from agent_profile_versions where tenant_id = %s "
        "order by version desc limit %s", (tenant_id, limit))
    return [{"version": r["version"], "created_at": r["created_at"].isoformat(),
             "seller_name": r["content"].get("seller_name"), "tone": r["content"].get("tone"),
             "content": r["content"]} for r in cur.fetchall()]


def restore(cur: Any, tenant_id: str, version: int, created_by: Optional[str]) -> Optional[dict[str, Any]]:
    """Vuelve a una versión anterior creando una versión NUEVA (el historial no se reescribe).
    El link público no se toca: restaurar no rompe la tienda compartida."""
    cur.execute("select content from agent_profile_versions where tenant_id = %s and version = %s",
                (tenant_id, version))
    row = cur.fetchone()
    if row is None:
        return None
    content = {k: v for k, v in row["content"].items() if k in _VERSIONED}
    return _update(cur, tenant_id, validate(content), created_by)


def _update(cur: Any, tenant_id: str, changes: dict[str, Any],
            created_by: Optional[str] = None) -> dict[str, Any]:
    """Aplica cambios y, si cambia algo del comportamiento, crea la versión siguiente."""
    current = _get(cur, tenant_id)
    changes = {k: v for k, v in changes.items() if current is None or current.get(k) != v}
    if changes:
        sets = ", ".join(f"{k} = %({k})s" + ("::jsonb" if k in _JSON_FIELDS else "") for k in changes)
        params = {k: (json.dumps(v) if k in _JSON_FIELDS else v) for k, v in changes.items()}
        params["tenant"] = tenant_id
        bump = any(k in _VERSIONED for k in changes)
        cur.execute(f"update agent_profiles set {sets}, updated_at = now()"
                    + (", version = version + 1" if bump else "") + " where tenant_id = %(tenant)s",
                    params)
        if bump:
            _snapshot(cur, tenant_id, _get(cur, tenant_id), created_by)
    return _get(cur, tenant_id)


def tenant_by_slug(slug: str) -> Optional[dict[str, str]]:
    """Negocio de un link público. El slug es un identificador PÚBLICO (como la URL de una
    tienda); el servidor resuelve el tenant, el cliente nunca lo envía."""
    if not re.fullmatch(r"[a-z0-9-]{3,48}", slug or ""):
        return None
    with system_tx() as cur:
        cur.execute("select p.tenant_id, t.name from agent_profiles p join tenants t on t.id = p.tenant_id "
                    "where p.public_slug = %s", (slug,))
        row = cur.fetchone()
    return {"tenant_id": str(row["tenant_id"]), "name": row["name"]} if row else None


def for_agent(tenant_id: str) -> Optional[dict[str, Any]]:
    """Perfil para el agente en cada turno (lectura del backend, tenant ya resuelto)."""
    from ..db import tenant_tx
    with tenant_tx(tenant_id) as cur:
        return _get(cur, tenant_id)
