"""Qué usa cada negocio: al registrarse (o después, en ajustes) elige sus módulos y el panel muestra
sólo eso. Un local de ropa no necesita reparto propio; una casa de electro sí; un taller vive de turnos.

Los módulos ordenan el panel y el asistente; las reglas de venta (zonas, retiro, turnos) siguen
saliendo de la configuración del agente, así que apagar un módulo nunca inventa ni borra datos.
"""
from __future__ import annotations

import json
from typing import Any

from . import opportunities

MODULES: dict[str, dict[str, str]] = {
    "turnos": {"label": "Turnos", "hint": "El agente agenda visitas, mediciones o servicios con cupo."},
    "reparto": {"label": "Reparto propio", "hint": "Entregás o instalás con tu gente: franjas, cupo y hoja de ruta."},
    "correo": {"label": "Envíos por correo", "hint": "Despachás por Andreani, OCA u otro y el cliente sigue su envío."},
    "retiro": {"label": "Retiro en el local", "hint": "El cliente pasa a buscar su compra."},
    "senas": {"label": "Señas", "hint": "Cobrás una seña en productos a pedido o a medida."},
    "campanias": {"label": "Campañas", "hint": "Le escribís a tus clientes: carritos que quedaron, cobranzas, novedades."},
}
# Negocios existentes: todo prendido (no desaparece nada que ya usaban).
DEFAULTS = {k: True for k in MODULES}


def get(cur: Any, tenant_id: str) -> dict[str, bool]:
    cur.execute("select settings_json -> 'modules' as m from tenants where id = %s", (tenant_id,))
    row = cur.fetchone()
    saved = (row or {}).get("m") or {}
    return {k: bool(saved.get(k, DEFAULTS[k])) for k in MODULES}


def save(cur: Any, tenant_id: str, uid: str, data: Any) -> dict[str, bool]:
    if not isinstance(data, dict) or any(k not in MODULES for k in data):
        raise ValueError("Módulo desconocido.")
    current = get(cur, tenant_id)
    current.update({k: bool(v) for k, v in data.items()})
    cur.execute("update tenants set settings_json = jsonb_set(coalesce(settings_json, '{}'::jsonb), '{modules}', %s::jsonb) "
                "where id = %s", (json.dumps(current), tenant_id))
    opportunities._audit(cur, tenant_id, "modules_updated", None, {"actor": uid, "modules": current})
    return current


def catalog() -> list[dict[str, str]]:
    return [{"key": k, **v} for k, v in MODULES.items()]
