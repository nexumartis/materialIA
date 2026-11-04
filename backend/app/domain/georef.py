"""Ubicar lo que escribe el cliente con la API Georef (datos.gob.ar, oficial, gratis, sin clave):
«Bernal» → localidad del partido de Quilmes, Buenos Aires. Sirve para que una zona de envío
cargada como «Quilmes» o «Zona Sur» responda por las localidades que la componen.

Nunca inventa una zona: sólo amplía los nombres con los que se compara. Si Georef no responde
(timeout corto) se sigue con la comparación por texto de siempre.
"""
from __future__ import annotations

import logging
import time

from typing import Any, Optional

import httpx

from ..config import settings
from .inventory import normalize

log = logging.getLogger(__name__)

TIMEOUT_S = 3.0
_TTL_S = 24 * 3600
_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}
_MAX_CACHE = 1000

_CABA = "ciudad autonoma de buenos aires"
_CABA_ALIASES = ("caba", "capital federal", "capital", "ciudad de buenos aires")

# Partidos del conurbano por zona, como los nombra la gente. General San Martín queda afuera a
# propósito: unos lo cuentan en el norte y otros en el oeste (decisión de Claude).
_GBA = {
    "zona norte": ("San Isidro", "Vicente López", "San Fernando", "Tigre", "Escobar", "Pilar",
                   "Malvinas Argentinas", "José C. Paz", "San Miguel"),
    "zona oeste": ("La Matanza", "Morón", "Hurlingham", "Ituzaingó", "Tres de Febrero", "Merlo",
                   "Moreno", "General Rodríguez", "Marcos Paz"),
    "zona sur": ("Avellaneda", "Lanús", "Lomas de Zamora", "Quilmes", "Berazategui", "Florencio Varela",
                 "Almirante Brown", "Esteban Echeverría", "Ezeiza", "Presidente Perón", "San Vicente"),
}
_GBA_ZONE = {normalize(p): z for z, ps in _GBA.items() for p in ps}


def _fetch(name: str) -> list[dict[str, str]]:
    r = httpx.get(f"{settings.georef_url.rstrip('/')}/localidades", timeout=TIMEOUT_S, params={
        "nombre": name, "max": 10, "campos": "nombre,municipio.nombre,departamento.nombre,provincia.nombre"})
    r.raise_for_status()
    return [{"localidad": x.get("nombre") or "", "municipio": (x.get("municipio") or {}).get("nombre") or "",
             "departamento": (x.get("departamento") or {}).get("nombre") or "",
             "provincia": (x.get("provincia") or {}).get("nombre") or ""}
            for x in r.json().get("localidades", [])]


def places(name: str) -> list[dict[str, str]]:
    """Localidades que se llaman así (o empiezan así: «Bernal» incluye «Bernal Oeste»). [] si
    Georef está apagado, no responde o el texto es muy corto."""
    q = normalize(name)
    if not settings.georef_url or len(q) < 3 or len(q) > 60:
        return []
    hit = _cache.get(q)
    if hit and time.monotonic() - hit[0] < _TTL_S:
        return hit[1]
    try:
        found = [p for p in _fetch(q) if normalize(p["localidad"]) == q or normalize(p["localidad"]).startswith(q + " ")]
    except (httpx.HTTPError, ValueError):
        log.info("georef no respondió para %r: sigo con la comparación por texto", q)
        return []
    if len(_cache) >= _MAX_CACHE:
        _cache.clear()
    _cache[q] = (time.monotonic(), found)
    return found


def names_for(place: dict[str, str]) -> set[str]:
    """Nombres (normalizados) por los que un negocio puede haber cargado la zona de ese lugar."""
    out = {normalize(place[k]) for k in ("localidad", "municipio", "departamento", "provincia") if place[k]}
    if normalize(place["provincia"]) == _CABA:
        out.update(_CABA_ALIASES)
    if normalize(place["provincia"]) == "buenos aires":
        zone = _GBA_ZONE.get(normalize(place["departamento"])) or _GBA_ZONE.get(normalize(place["municipio"]))
        if zone:
            out.update({zone, "gba", "gran buenos aires", "conurbano", "amba"})
    out.discard("")
    return out


def describe(place: dict[str, str]) -> str:
    """«Bernal (Quilmes, Buenos Aires)» para explicarle al cliente cómo se entendió."""
    where = [x for x in (place["departamento"], place["provincia"]) if x and x != place["localidad"]]
    return place["localidad"] + (f" ({', '.join(where)})" if where else "")


def match_zone(text: str, zones: list[str]) -> tuple[str | None, list[dict[str, str]]]:
    """(zona del negocio que cubre ese lugar, lugares encontrados). Con varios lugares homónimos en
    distintos partidos, sólo hay respuesta si TODOS caen en la misma zona (si no, None y se repregunta)."""
    found = places(text)
    if not found:
        return None, []
    norm = {normalize(z): z for z in zones}
    hits = {next((norm[n] for n in names_for(p) if n in norm), None) for p in found}
    if len(hits) == 1 and None not in hits:
        return hits.pop(), found
    return None, found


def address(street: str, place: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Dirección normalizada (calle, altura, localidad, partido, provincia) o None. Con lugar prueba
    como localidad, como partido y, si no, sin filtro («zona sur» o un lugar mal escrito no traban)."""
    if not settings.georef_url or not street:
        return None
    for key in (["localidad", "departamento", None] if place else [None]):
        params = {"direccion": street, "max": 1, "campos": "calle.nombre,altura.valor,localidad_censal.nombre,"
                  "departamento.nombre,provincia.nombre,nomenclatura"}
        if key:
            params[key] = place
        try:
            r = httpx.get(f"{settings.georef_url.rstrip('/')}/direcciones", params=params, timeout=TIMEOUT_S)
            r.raise_for_status()
            found = r.json().get("direcciones") or []
        except (httpx.HTTPError, ValueError):
            log.info("georef no respondió para una dirección")
            return None
        if found and (found[0].get("altura") or {}).get("valor"):
            d = found[0]
            out = {"calle": d["calle"]["nombre"], "altura": d["altura"]["valor"],
                   "localidad": (d.get("localidad_censal") or {}).get("nombre") or "",
                   "departamento": (d.get("departamento") or {}).get("nombre") or "",
                   "provincia": (d.get("provincia") or {}).get("nombre") or ""}
            out["texto"] = d.get("nomenclatura") or ", ".join(
                x for x in (f"{out['calle']} {out['altura']}", out["localidad"], out["provincia"]) if x)
            return out
    return None
