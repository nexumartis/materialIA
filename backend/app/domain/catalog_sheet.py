"""Google Sheets como catálogo vivo: el dueño conecta una planilla pública y se sincroniza con
el catálogo usando el mismo formato y las mismas validaciones que el CSV.

Seguridad: sólo se aceptan links de docs.google.com/spreadsheets; el servidor ARMA la URL de
exportación con el ID (nunca descarga una URL que manda el usuario) y cada redirección se valida
contra una lista de dominios de Google. Sin OAuth ni credenciales: la planilla tiene que estar
compartida como «cualquier persona con el enlace puede ver» o publicada en la web.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import httpx

from ..db import system_tx, tenant_tx
from . import backoffice, opportunities

log = logging.getLogger(__name__)

MAX_BYTES = 2_000_000           # mismo tope que el CSV subido a mano
TIMEOUT_S = 15.0                # por operación de red
MAX_DOWNLOAD_S = 30.0           # total de la descarga (una respuesta lenta no traba al worker)
SYNC_EVERY = "15 minutes"
WORKER_BUDGET_S = 45.0          # por vuelta del worker: el resto de sus tareas no espera de más
# /spreadsheets/d/<ID>, /spreadsheets/u/<n>/d/<ID> (multi-cuenta) y /spreadsheets/d/e/<ID> (publicada).
_PATH = re.compile(r"^/spreadsheets/(?:u/\d+/)?d/(e/)?([A-Za-z0-9_-]{20,120})(?:/|$)")
_ALLOWED_HOSTS = ("docs.google.com",)
_ALLOWED_SUFFIXES = (".googleusercontent.com",)
_PRIVATE = ("La planilla es privada: compartila como «cualquier persona con el enlace puede ver» "
            "(o publicala en la web).")


class SheetError(ValueError):
    """La planilla no se pudo leer (link inválido, privada, caída, demasiado grande). Mensaje para el dueño."""


def parse_url(url: str) -> tuple[str, str, bool]:
    """(sheet_id, gid, publicada) de un link de Google Sheets. SheetError si no es uno."""
    raw = (url or "").strip()
    if raw.startswith("docs.google.com/"):
        raw = "https://" + raw                     # pegado sin el https://
    try:
        u = urlparse(raw)
    except ValueError:
        raise SheetError("El link no es válido.") from None
    m = _PATH.match(u.path or "")
    if u.scheme != "https" or u.hostname != "docs.google.com" or not m:
        raise SheetError("Pegá el link de una planilla de Google Sheets (docs.google.com/spreadsheets/…).")
    gid = (parse_qs(u.query).get("gid") or parse_qs(u.fragment).get("gid") or ["0"])[0]
    if not re.fullmatch(r"[0-9]{1,12}", gid):
        raise SheetError("La pestaña indicada en el link no es válida.")
    return m.group(2), gid, bool(m.group(1))


def export_url(sheet_id: str, gid: str, published: bool = False) -> str:
    if published:
        return f"https://docs.google.com/spreadsheets/d/e/{sheet_id}/pub?output=csv&gid={gid}&single=true"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _host_ok(host: Optional[str]) -> bool:
    return bool(host) and (host in _ALLOWED_HOSTS or host.endswith(_ALLOWED_SUFFIXES))


def fetch_csv(sheet_id: str, gid: str, published: bool = False) -> str:
    """Descarga la pestaña como CSV. Valida el dominio en cada redirección, el tamaño, el tiempo
    total y el tipo de respuesta."""
    def guard(request: httpx.Request) -> None:
        if request.url.host == "accounts.google.com":
            # Una planilla privada redirige al login de Google: no es un sitio raro, es falta de permiso.
            raise SheetError(_PRIVATE)
        if request.url.scheme != "https" or not _host_ok(request.url.host):
            raise SheetError("La planilla redirigió a un sitio no permitido.")

    started = time.monotonic()
    try:
        with httpx.Client(timeout=TIMEOUT_S, follow_redirects=True, max_redirects=5,
                          event_hooks={"request": [guard]}) as client:
            with client.stream("GET", export_url(sheet_id, gid, published)) as r:
                if r.status_code in (401, 403, 404):
                    raise SheetError("No pude abrir la planilla: compartila como «cualquier persona con el "
                                     "enlace puede ver» y revisá que el link sea correcto.")
                if r.status_code >= 400:
                    raise SheetError(f"Google respondió un error ({r.status_code}). Probá de nuevo en un rato.")
                if "text/html" in r.headers.get("content-type", ""):
                    raise SheetError(_PRIVATE)    # página de login en lugar del CSV
                data = bytearray()
                for chunk in r.iter_bytes():
                    data += chunk
                    if len(data) > MAX_BYTES:
                        raise SheetError("La planilla es demasiado grande (máx. 2 MB).")
                    if time.monotonic() - started > MAX_DOWNLOAD_S:
                        raise SheetError("La planilla tardó demasiado en descargarse. Probá de nuevo en un rato.")
    except httpx.HTTPError:
        raise SheetError("No pude conectarme con Google Sheets. Probá de nuevo en un rato.") from None
    return bytes(data).decode("utf-8-sig", errors="replace")


# --- Fuente del negocio -----------------------------------------------------------------
def _view(row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    url = (f"https://docs.google.com/spreadsheets/d/e/{row['sheet_id']}/pubhtml?gid={row['gid']}" if row["published"]
           else f"https://docs.google.com/spreadsheets/d/{row['sheet_id']}/edit#gid={row['gid']}")
    return {
        "url": url, "enabled": row["enabled"],
        "last_synced_at": row["last_synced_at"].isoformat() if row["last_synced_at"] else None,
        "last_status": row["last_status"], "last_result": row["last_result"], "last_error": row["last_error"],
    }


def get(cur: Any, tenant_id: str) -> Optional[dict[str, Any]]:
    cur.execute("select sheet_id, gid, published, enabled, last_synced_at, last_status, last_result, last_error "
                "from catalog_sources where tenant_id = %s", (tenant_id,))
    return _view(cur.fetchone())


def _forget_sheet_stock(cur: Any, tenant_id: str) -> None:
    """Una planilla (re)conectada o desconectada pasa a ser, o deja de ser, la fuente del stock:
    se olvida lo leído de la anterior para que su primer valor se aplique."""
    cur.execute("update catalog_items set sheet_stock = null where tenant_id = %s and sheet_stock is not null",
                (tenant_id,))


def connect(cur: Any, tenant_id: str, uid: str, url: str) -> None:
    """Guarda (o reemplaza) la planilla del negocio. La primera sincronización la hace `sync`."""
    sheet_id, gid, published = parse_url(url)
    cur.execute(
        "insert into catalog_sources (tenant_id, sheet_id, gid, published, created_by) values (%s, %s, %s, %s, %s) "
        "on conflict (tenant_id) do update set sheet_id = excluded.sheet_id, gid = excluded.gid, "
        "published = excluded.published, enabled = true, last_synced_at = null, last_status = null, "
        "last_result = null, last_error = null, updated_at = now()",
        (tenant_id, sheet_id, gid, published, uid))
    _forget_sheet_stock(cur, tenant_id)
    opportunities._audit(cur, tenant_id, "catalog_sheet_connected", None, {"actor": uid, "sheet_id": sheet_id})


def disconnect(cur: Any, tenant_id: str, uid: str) -> bool:
    cur.execute("delete from catalog_sources where tenant_id = %s", (tenant_id,))
    if not cur.rowcount:
        return False
    _forget_sheet_stock(cur, tenant_id)
    opportunities._audit(cur, tenant_id, "catalog_sheet_disconnected", None, {"actor": uid})
    return True


def _record(tenant_id: str, status: str, result: Optional[dict[str, Any]] = None, error: Optional[str] = None) -> None:
    with tenant_tx(tenant_id) as cur:
        cur.execute("update catalog_sources set last_synced_at = now(), last_status = %s, "
                    "last_result = coalesce(%s::jsonb, last_result), last_error = %s, updated_at = now() "
                    "where tenant_id = %s",
                    (status, json.dumps(result, ensure_ascii=False) if result else None, error, tenant_id))


def sync(tenant_id: str) -> Optional[dict[str, Any]]:
    """Lee la planilla (fuera de la transacción) y la importa. Devuelve el estado o None si no hay
    planilla conectada. Cualquier falla queda registrada en la fuente y no se propaga."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("select sheet_id, gid, published from catalog_sources where tenant_id = %s and enabled",
                    (tenant_id,))
        src = cur.fetchone()
    if src is None:
        return None
    try:
        text = fetch_csv(src["sheet_id"], src["gid"], src["published"])
        with tenant_tx(tenant_id) as cur:
            # Bloquea la fuente: una sincronización manual y la del worker no importan a la vez
            # (la segunda espera y reaplica los mismos datos sin duplicar precios).
            cur.execute("select 1 from catalog_sources where tenant_id = %s for update", (tenant_id,))
            if cur.fetchone() is None:
                return None                     # la desconectaron mientras se descargaba
            result = backoffice.import_csv(cur, tenant_id, text, from_sheet=True)
            cur.execute("update catalog_sources set last_synced_at = now(), last_status = 'ok', last_result = %s::jsonb, "
                        "last_error = null, updated_at = now() where tenant_id = %s",
                        (json.dumps(result, ensure_ascii=False), tenant_id))
            if result["created"] or result["changes"]["prices"] or result["changes"]["stock"]:
                opportunities._audit(cur, tenant_id, "catalog_sheet_synced", None, {
                    "created": result["created"], "prices": result["changes"]["prices"],
                    "stock": result["changes"]["stock"], "errors": len(result["errors"])})
    except (SheetError, ValueError) as exc:     # ValueError: CSV vacío o sin columnas obligatorias
        _record(tenant_id, "error", error=str(exc))
    except Exception:  # noqa: BLE001 - un error inesperado se registra como error de lectura, no queda colgado
        log.exception("sincronización de planilla falló para %s", tenant_id)
        _record(tenant_id, "error", error="No pude procesar la planilla. Revisá el formato y probá de nuevo.")
    with tenant_tx(tenant_id) as cur:
        return get(cur, tenant_id)


def sync_due(limit: int = 10, budget_s: float = WORKER_BUDGET_S) -> int:
    """Worker: sincroniza, de a una, las planillas que no se leyeron en los últimos 15 minutos.
    Cada una se reclama marcando la hora antes de leerla (dos workers no la leen a la vez). Pasado
    `budget_s` no reclama más: las demás quedan para la vuelta siguiente."""
    started, done = time.monotonic(), 0
    while done < limit and (done == 0 or time.monotonic() - started < budget_s):
        with system_tx() as cur:
            cur.execute(
                "update catalog_sources set last_synced_at = now() where tenant_id = ("
                " select tenant_id from catalog_sources where enabled and (last_synced_at is null "
                f" or last_synced_at < now() - interval '{SYNC_EVERY}') order by last_synced_at nulls first "
                " for update skip locked limit 1) returning tenant_id")
            row = cur.fetchone()
        if row is None:
            break
        done += 1
        try:
            sync(str(row["tenant_id"]))
        except Exception:  # noqa: BLE001 - una planilla no frena a las demás
            log.exception("sincronización de planilla falló para %s", row["tenant_id"])
    return done
