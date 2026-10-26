"""Proveedores de pago detrás de una interfaz única.

- `SimulatedProvider`: sin credenciales. Su "servidor" es la tabla `sim_provider_payments`; sus
  avisos se firman y verifican con el MISMO esquema que Mercado Pago, así el flujo de webhook,
  verificación y consulta del pago es el real. Siempre se rotula `simulated`.
- `MercadoPagoProvider`: Checkout Pro por API REST (preferencias y consulta de pagos). Firma de
  avisos `x-signature` según la documentación pública de Mercado Pago. No verificado contra la
  plataforma real en este repo: requiere credenciales de prueba (ver .env.example).

Regla: el estado de un pago SIEMPRE se obtiene consultando al proveedor (`fetch_payment`), nunca
del cuerpo del aviso ni de lo que diga el cliente.
"""
from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from ..config import settings
from ..db import system_tx


class PaymentProviderError(Exception):
    """El proveedor no respondió o rechazó la operación (reintentable)."""


@dataclass
class Checkout:
    preference_id: str
    url: str


@dataclass
class ProviderPayment:
    id: str
    status: str                 # approved | pending | in_process | rejected | cancelled | refunded | charged_back
    external_reference: str     # id del pedido
    amount: float
    currency: str


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, order: dict[str, Any]) -> Checkout: ...
    def fetch_payment(self, payment_id: str) -> Optional[ProviderPayment]: ...
    def verify_notification(self, headers: dict[str, str], data_id: str) -> bool: ...


# --- Firma de avisos (esquema x-signature de Mercado Pago) ------------------------
def _manifest(data_id: str, request_id: str, ts: str) -> str:
    # Mercado Pago: `id:[data.id];request-id:[x-request-id];ts:[ts];`, el data.id en minúsculas
    # si es alfanumérico y omitiendo las partes que no vinieron en el aviso.
    parts = [("id", data_id.lower()), ("request-id", request_id), ("ts", ts)]
    return "".join(f"{k}:{v};" for k, v in parts if v)


def sign_notification(secret: str, data_id: str, request_id: str, ts: Optional[str] = None) -> dict[str, str]:
    ts = ts or str(int(time.time()))
    v1 = hmac.new(secret.encode(), _manifest(data_id, request_id, ts).encode(), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


def verify_signature(secret: Optional[str], headers: dict[str, str], data_id: str) -> bool:
    if not secret or not data_id:
        return False
    lower = {k.lower(): v for k, v in headers.items()}
    parts = dict(p.strip().split("=", 1) for p in lower.get("x-signature", "").split(",") if "=" in p)
    ts, v1, request_id = parts.get("ts"), parts.get("v1"), lower.get("x-request-id", "")
    if not ts or not v1:
        return False
    expected = hmac.new(secret.encode(), _manifest(data_id, request_id, ts).encode(),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


# --- Simulado -----------------------------------------------------------------
class SimulatedProvider:
    name = "simulated"

    def create_checkout(self, order: dict[str, Any]) -> Checkout:
        pref = f"sim-pref-{uuid.uuid4()}"
        return Checkout(pref, f"{settings.public_base_url.rstrip('/')}/sandbox/checkout/{pref}")

    def fetch_payment(self, payment_id: str) -> Optional[ProviderPayment]:
        try:
            uuid.UUID(payment_id)
        except ValueError:
            return None
        with system_tx() as cur:
            cur.execute("select id, status, external_ref, amount, currency from sim_provider_payments "
                        "where id = %s", (payment_id,))
            r = cur.fetchone()
        if r is None:
            return None
        return ProviderPayment(str(r["id"]), r["status"], r["external_ref"], float(r["amount"]), r["currency"])

    def verify_notification(self, headers: dict[str, str], data_id: str) -> bool:
        return verify_signature(settings.sim_webhook_secret, headers, data_id)

    # Lo que en la realidad hace el comprador en la página de Mercado Pago.
    def pay(self, preference_id: str, outcome: str) -> tuple[dict[str, str], dict[str, Any]]:
        """Registra el pago en el "servidor" simulado y devuelve el aviso firmado (headers, body)."""
        if outcome not in ("approved", "rejected", "pending"):
            raise ValueError("resultado simulado inválido")
        with system_tx() as cur:
            # La preferencia cobra el total del pedido (como el ítem de una preferencia real).
            cur.execute("select p.order_id, o.total as amount, o.currency from payments p "
                        "join orders o on o.tenant_id = p.tenant_id and o.id = p.order_id "
                        "where p.provider = 'simulated' and p.preference_id = %s", (preference_id,))
            p = cur.fetchone()
            if p is None:
                raise LookupError("preferencia inexistente")
            cur.execute(
                "insert into sim_provider_payments (preference_id, external_ref, status, amount, currency) "
                "values (%s, %s, %s, %s, %s) returning id",
                (preference_id, str(p["order_id"]), outcome, p["amount"], p["currency"]),
            )
            payment_id = str(cur.fetchone()["id"])
        headers = sign_notification(settings.sim_webhook_secret, payment_id, str(uuid.uuid4()))
        return headers, {"type": "payment", "action": "payment.created", "data": {"id": payment_id}}


# --- Mercado Pago ---------------------------------------------------------------
class MercadoPagoProvider:
    name = "mercadopago"

    def __init__(self, client: Optional[httpx.Client] = None):
        if not settings.mp_access_token:
            raise PaymentProviderError("Falta MP_ACCESS_TOKEN (usar credenciales de PRUEBA).")
        self._client = client or httpx.Client(base_url=settings.mp_api_base, timeout=15.0)
        self._auth = {"Authorization": f"Bearer {settings.mp_access_token}"}

    def create_checkout(self, order: dict[str, Any]) -> Checkout:
        base = settings.public_base_url.rstrip("/")
        body = {
            "items": [{"id": it["sku"], "title": it["name"], "quantity": it["qty"],
                       "unit_price": it["unit_price"], "currency_id": order["currency"]}
                      for it in order["items"]],
            "external_reference": order["id"],
            "notification_url": f"{base}/webhooks/mercadopago",
            "expires": bool(order.get("reserved_until")),
            "expiration_date_to": order.get("reserved_until"),
        }
        try:
            resp = self._client.post("/checkout/preferences", json=body, headers={
                **self._auth, "X-Idempotency-Key": f"order-{order['id']}"})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError(f"Mercado Pago no creó la preferencia ({type(exc).__name__})") from exc
        return Checkout(str(data["id"]), data["init_point"])

    def fetch_payment(self, payment_id: str) -> Optional[ProviderPayment]:
        try:
            resp = self._client.get(f"/v1/payments/{payment_id}", headers=self._auth)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            d = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError(f"Mercado Pago no respondió ({type(exc).__name__})") from exc
        return ProviderPayment(str(d["id"]), d["status"], str(d.get("external_reference") or ""),
                               float(d["transaction_amount"]), d.get("currency_id", "ARS"))

    def verify_notification(self, headers: dict[str, str], data_id: str) -> bool:
        return verify_signature(settings.mp_webhook_secret, headers, data_id)


def get_provider(name: Optional[str] = None) -> PaymentProvider:
    name = name or settings.payment_provider
    if name == "simulated":
        # El simulado (clave de firma pública, checkout sin cobro) sólo existe si es el proveedor
        # configurado: con Mercado Pago activo, sus rutas no pueden marcar pedidos como pagados.
        if settings.payment_provider != "simulated":
            raise PaymentProviderError("el proveedor simulado está deshabilitado")
        return SimulatedProvider()
    if name == "mercadopago":
        return MercadoPagoProvider()
    raise PaymentProviderError(f"proveedor de pago desconocido: {name}")
