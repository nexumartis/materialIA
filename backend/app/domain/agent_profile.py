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
           "shipping", "hours", "payment_methods")


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
    return {k: row[k] for k in _FIELDS} | {"updated_at": row["updated_at"].isoformat()}


def _get(cur: Any, tenant_id: str) -> Optional[dict[str, Any]]:
    cur.execute(f"select {', '.join(_FIELDS)}, updated_at from agent_profiles where tenant_id = %s",
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
    return _get(cur, tenant_id)


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
    return out


def _update(cur: Any, tenant_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if changes:
        sets = ", ".join(f"{k} = %({k})s" + ("::jsonb" if k in ("faq", "rules") else "") for k in changes)
        params = {k: (json.dumps(v) if k in ("faq", "rules") else v) for k, v in changes.items()}
        params["tenant"] = tenant_id
        cur.execute(f"update agent_profiles set {sets}, updated_at = now() where tenant_id = %(tenant)s",
                    params)
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
