"""Chat en la web del negocio: el dueño pega UNA línea (`<script src=".../widget.js" data-tienda="slug">`)
y el botón aparece en su sitio. El script lee la configuración en vivo (`public_config`), así que los
cambios del panel se ven sin volver a pegar nada.

- El negocio sale del slug (público, como la tienda): el sitio ajeno nunca manda un tenant.
- La charla corre en un iframe del dominio del panel: la página del comercio no ve la conversación.
- «Instalado en»: el script avisa el dominio donde se cargó (`seen`). Es informativo (cualquiera
  puede pegar el código en cualquier lado): se guarda sólo el host, con tope y escrituras espaciadas.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlsplit

from ..config import settings
from ..db import tenant_tx
from . import opportunities

DEFAULTS: dict[str, Any] = {"color": "#2563eb", "label": "¿Te ayudo?", "position": "right",
                            "greeting": "", "greeting_delay_s": 8}
MAX_HOSTS = 30
_HOST = re.compile(r"^(localhost|[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+|\d{1,3}(\.\d{1,3}){3})$")


def validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Configuración inválida.")
    out = dict(DEFAULTS)
    color = str(data.get("color", out["color"])).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("El color tiene que ser como #2563eb.")
    label = " ".join(str(data.get("label", out["label"])).split())
    if not 1 <= len(label) <= 40:
        raise ValueError("El texto del botón tiene que tener entre 1 y 40 caracteres.")
    position = data.get("position", out["position"])
    if position not in ("right", "left"):
        raise ValueError("Posición inválida.")
    greeting = " ".join(str(data.get("greeting") or "").split())
    if len(greeting) > 140:
        raise ValueError("El saludo puede tener hasta 140 caracteres.")
    try:
        delay = int(data.get("greeting_delay_s", out["greeting_delay_s"]))
    except (TypeError, ValueError):
        raise ValueError("Los segundos del saludo tienen que ser un número.") from None
    if not 0 <= delay <= 120:
        raise ValueError("El saludo aparece entre 0 y 120 segundos después.")
    return {"color": color.lower(), "label": label, "position": position, "greeting": greeting,
            "greeting_delay_s": delay}


def _config(cur: Any, tenant_id: str) -> dict[str, Any]:
    cur.execute("select config from widget_settings where tenant_id = %s", (tenant_id,))
    row = cur.fetchone()
    return {**DEFAULTS, **(row["config"] if row else {})}


def script_url() -> str:
    return f"{settings.public_base_url.rstrip('/')}/widget.js"


def store_url(slug: str) -> str:
    return f"{settings.public_web_url.rstrip('/')}/?embed=1#/tienda/{slug}"


def snippet(slug: str) -> str:
    return f'<script src="{script_url()}" data-tienda="{slug}" async></script>'


def panel(cur: Any, tenant_id: str, slug: str) -> dict[str, Any]:
    cur.execute("select host, first_seen, last_seen, hits from widget_installs where tenant_id = %s "
                "order by last_seen desc limit 10", (tenant_id,))
    installs = [{"host": r["host"], "first_seen": r["first_seen"].isoformat(), "last_seen": r["last_seen"].isoformat(),
                 "hits": r["hits"]} for r in cur.fetchall()]
    return {"slug": slug, "store_url": store_url(slug), "script_url": script_url(), "snippet": snippet(slug),
            "config": _config(cur, tenant_id), "installs": installs}


def save(cur: Any, tenant_id: str, uid: str, slug: str, data: Any) -> dict[str, Any]:
    config = validate(data)
    cur.execute("insert into widget_settings (tenant_id, config, updated_by) values (%s, %s::jsonb, %s) "
                "on conflict (tenant_id) do update set config = excluded.config, updated_by = excluded.updated_by, "
                "updated_at = now()", (tenant_id, json.dumps(config), uid))
    opportunities._audit(cur, tenant_id, "widget_updated", None, {"actor": uid})
    return {"config": config, "snippet": snippet(slug)}


def public_config(tenant_id: str, slug: str) -> dict[str, Any]:
    with tenant_tx(tenant_id) as cur:
        return {**_config(cur, tenant_id), "store_url": store_url(slug)}


def host_of(page: Any) -> Optional[str]:
    try:
        parts = urlsplit(str(page or "")[:300])
    except ValueError:
        return None
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in ("http", "https") or not _HOST.fullmatch(host):
        return None
    return host[4:] if host.startswith("www.") else host


def seen(tenant_id: str, page: Any) -> bool:
    """Registra el dominio donde se cargó el script. Una escritura cada 10 minutos por dominio y, como
    mucho, `MAX_HOSTS` dominios por negocio (lo inventado por terceros no llena la tabla)."""
    host = host_of(page)
    if host is None:
        return False
    with tenant_tx(tenant_id) as cur:
        cur.execute("update widget_installs set last_seen = now(), hits = hits + 1 where tenant_id = %s and host = %s "
                    "and last_seen < now() - interval '10 minutes' returning 1", (tenant_id, host))
        if cur.fetchone():
            return True
        cur.execute("select count(*) as n, bool_or(host = %s) as known from widget_installs where tenant_id = %s",
                    (host, tenant_id))
        row = cur.fetchone()
        if row["known"] or row["n"] >= MAX_HOSTS:
            return False
        cur.execute("insert into widget_installs (tenant_id, host) values (%s, %s) on conflict do nothing", (tenant_id, host))
        return True
