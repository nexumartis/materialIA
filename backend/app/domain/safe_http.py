"""Pedidos HTTP del servidor hacia URLs que carga un usuario (leer su web, webhooks): sólo hacia
direcciones PÚBLICAS. Se resuelve el nombre una vez, se exige que TODAS sus IPs sean públicas
(ni localhost, ni red privada, ni metadatos de la nube, ni IPv6 mapeadas) y se conecta a esa IP ya
verificada con el nombre en Host/SNI: un DNS que cambia entre la verificación y la conexión
(rebinding) no llega a la red interna."""
from __future__ import annotations

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse


class UnsafeURL(ValueError):
    """La URL no apunta a un destino público permitido. `reason`: 'scheme' (esquema, usuario o host
    mal formados) o 'address' (resuelve a una dirección no pública)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def vetted_ip(host: Optional[str]) -> str:
    """IP pública a la que conectarse. UnsafeURL si alguna IP del nombre no es pública; LookupError
    si el nombre no existe."""
    if not host:
        raise UnsafeURL("scheme")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise LookupError(host) from None
    ips = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:   # ::ffff:127.0.0.1
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise UnsafeURL("address")
        ips.append(str(ip))
    if not ips:
        raise UnsafeURL("address")
    return ips[0]


def pinned(url: str, schemes: tuple[str, ...] = ("https",)) -> tuple[str, dict[str, str], dict[str, str]]:
    """(url hacia la IP verificada, headers con Host, extensions con SNI) para httpx."""
    u = urlparse(url)
    if u.scheme not in schemes or not u.hostname or u.username or u.password:
        raise UnsafeURL("scheme")
    ip = vetted_ip(u.hostname)
    port = f":{u.port}" if u.port else ""
    netloc = (f"[{ip}]" if ":" in ip else ip) + port
    return u._replace(netloc=netloc).geturl(), {"Host": u.hostname + port}, {"sni_hostname": u.hostname}
