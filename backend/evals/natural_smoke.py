"""Smoke cualitativo de conversación con un modelo LOCAL de Ollama (no reemplaza los tests).

Uso (desde backend/, con DATABASE_URL de una base local descartable con migraciones):
    python evals/natural_smoke.py salida.json

Crea un negocio sintético propio, corre conversaciones fijas y lo borra al final. Tope duro de
llamadas al modelo (SMOKE_MAX_CALLS, 20): al llegar, el planner falla y responde el respaldo.
Criterios fijados antes de correr (CRITERIA); se registran todas las respuestas, no sólo éxitos.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from app.agent import llm_sales  # noqa: E402
from app.agent.sales_agent import handle_sales_message  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import connect  # noqa: E402
from app.domain import orders  # noqa: E402
from app.payments import service  # noqa: E402
from app.payments.providers import SimulatedProvider  # noqa: E402
from conftest import _SHOP_ITEMS  # noqa: E402

MODEL = os.environ.get("SMOKE_MODEL", "qwen3:8b")
BASE = os.environ.get("SMOKE_OLLAMA_URL", "http://127.0.0.1:11434")
MAX_CALLS = int(os.environ.get("SMOKE_MAX_CALLS", "20"))
CASES = set(filter(None, os.environ.get("SMOKE_CASES", "").split(",")))   # vacío = todos

CRITERIA = {
    "gracias_pagado": "no pide pagar, no ofrece email/WhatsApp, sin pregunta de venta; pedido sigue PAID",
    "busqueda": "precios/stock sólo del catálogo; opciones de cocina negras",
    "correccion_color": "conserva 'cocina' (no ofrece lavatorio como si fuera de cocina) o dice que no hay",
    "comparacion": "diferencia sustentada en nombre/ficha; precio correcto por producto",
    "comparacion_reglas": "lista armada por reglas; compara negra mate vs pico extraíble con hechos de ficha "
                          "($89.900 / $129.000), sin rasgos inventados (vía comparar_productos o respaldo)",
    "canal": "no promete avisar por WhatsApp/email; ofrece lo que puede hacer en el chat",
    "ya_pague": "no da por pagado; pedido sigue PENDING_PAYMENT",
    "plazo": "no promete 'mañana'; usa lo que informa el negocio o deriva",
}
_BAD = {
    "pide_pagar": re.compile(r"\b(pagar|pagá|link de pago)\b", re.I),
    "canal": re.compile(r"\b(e-?mail|correo|whatsapp|sms)\b", re.I),
    "manana": re.compile(r"\bmañana\b", re.I),
    "acreditado": re.compile(r"\b(acreditad[oa]|pagad[oa])\b", re.I),
}

calls: list[dict] = []


def counted_planner(messages, tools):
    if len(calls) >= MAX_CALLS:
        calls.append({"skipped": "tope de llamadas"})
        raise RuntimeError("tope de llamadas del smoke")
    t0 = time.monotonic()
    entry = {"tools_offered": len(tools)}
    try:
        out = llm_sales._ollama_planner(messages, tools)
        entry.update(content=out["content"], tool_calls=out["tool_calls"])
        return out
    except Exception as exc:  # se registra y se propaga: el agente decide el respaldo
        entry["error"] = repr(exc)[:300]
        raise
    finally:
        entry["latency_s"] = round(time.monotonic() - t0, 2)
        calls.append(entry)


def make_shop(conn) -> str:
    tid = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("insert into tenants (id, name) values (%s, 'Sanitarios Smoke (SINTÉTICA)')", (tid,))
        for _key, sku, name, cat, mode, specs, price, stock in _SHOP_ITEMS:
            cur.execute("insert into catalog_items (tenant_id, sku, name, category, pricing_mode, specs_json, "
                        "brand) values (%s, %s, %s, %s, %s, %s::jsonb, 'Marca Test') returning id",
                        (tid, sku, name, cat, mode, json.dumps(specs)))
            iid = cur.fetchone()["id"]
            if price is not None:
                cur.execute("insert into price_entries (tenant_id, item_id, amount, valid_from) "
                            "values (%s, %s, %s, date '2026-01-01')", (tid, iid, price))
            if stock is not None:
                cur.execute("insert into stock_levels (tenant_id, item_id, on_hand) values (%s, %s, %s)",
                            (tid, iid, stock))
        cur.execute("insert into agent_profiles (tenant_id, public_slug, seller_name, tone, shipping, "
                    "payment_methods) values (%s, %s, 'Sofi', 'cercano', %s, %s)",
                    (tid, f"smoke-{tid[:8]}", "Envíos en CABA y GBA; costo y plazo los confirma el equipo.",
                     "Mercado Pago o transferencia."))
    conn.commit()
    return tid


def drop_shop(conn, tid: str) -> None:
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("delete from sim_provider_payments where external_ref in "
                    "(select id::text from orders where tenant_id = %s)", (tid,))
        cur.execute("delete from tenants where id = %s", (tid,))
    conn.commit()


def buy(tid: str, product: str, pay: bool) -> str:
    """Compra por reglas (sin modelo) hasta el link; opcionalmente paga con el proveedor simulado."""
    conv = handle_sales_message(tid, f"busco {product}").conversation_id
    for text in ("agregame la primera", "la compro", "sí"):
        r = handle_sales_message(tid, text, conv)
    if pay:
        pref = r.orders[0]["payment"]["checkout_url"].rsplit("/", 1)[1]
        headers, body = SimulatedProvider().pay(pref, "approved")
        service.receive_notification("simulated", headers, {}, body)
    return conv


def main(out_path: str) -> None:
    if urlparse(BASE).hostname not in ("127.0.0.1", "localhost"):
        sys.exit("El smoke sólo usa un Ollama local.")
    settings.ollama_base_url, settings.ollama_model = BASE, MODEL
    settings.llm_timeout_s = float(os.environ.get("SMOKE_TIMEOUT_S", "120"))
    conn = connect()
    tid = make_shop(conn)
    turns = []

    def live(case: str, conv, text: str):
        if CASES and case not in CASES:
            return conv
        settings.llm_provider = "ollama"
        start = len(calls)
        t0 = time.monotonic()
        r = handle_sales_message(tid, text, conv, planner=counted_planner)
        settings.llm_provider = "mock"
        status = [o["status"] for o in orders.conversation_orders(tid, r.conversation_id)]
        turns.append({"case": case, "criterio": CRITERIA[case], "cliente": text, "respuesta": r.reply,
                      "mode": r.mode, "requires_human": r.requires_human, "pedidos": status,
                      "controles": [t["summary"] for t in r.trace if t["name"] == "control"],
                      "herramientas": [t["name"] for t in r.trace if t["name"] != "control"],
                      "llamadas": calls[start:], "turno_s": round(time.monotonic() - t0, 2),
                      "alertas": [k for k, rx in _BAD.items() if rx.search(r.reply)]})
        return r.conversation_id

    try:
        settings.llm_provider = "mock"
        paid = buy(tid, "flexible 40 cm", pay=True)
        live("gracias_pagado", paid, "gracias!")
        conv = live("busqueda", None, "Hola! busco una canilla negra para la cocina")
        live("correccion_color", conv, "mmm y en cromo?")
        live("comparacion", conv, "qué diferencia hay entre la negra mate y la de pico extraíble?")
        live("canal", conv, "me avisás por whatsapp cuando entre la de lavatorio negra?")
        if not CASES or "comparacion_reglas" in CASES:
            listed = handle_sales_message(tid, "busco canilla negra para cocina").conversation_id  # reglas
            live("comparacion_reglas", listed, "qué diferencia hay entre la negra mate y la de pico extraíble?")
        pending = buy(tid, "canilla de lavatorio cromo", pay=False)
        live("ya_pague", pending, "ya pagué")
        live("plazo", pending, "y me llega mañana a Córdoba?")
    finally:
        settings.llm_provider = "mock"
        drop_shop(conn, tid)
        conn.close()
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"model": MODEL, "base_url": BASE, "max_calls": MAX_CALLS,
                   "model_calls": len([c for c in calls if "skipped" not in c]), "turns": turns},
                  fh, ensure_ascii=False, indent=2)
    print(f"{len(turns)} turnos, {len(calls)} llamadas registradas -> {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "natural-smoke.json")
