"""Fotos del cliente: sin modelo de visión la tienda no las ofrece; con modelo, la foto se describe como
búsqueda y el agente responde con el catálogo real. Un archivo que no es imagen se rechaza, los
metadatos se borran, la duda pide que el cliente lo cuente, y hay límites por IP."""
from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import auth
from app.config import settings
from app.domain import vision
from app.main import app
from jwt_helpers import KEY
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seen(monkeypatch):
    """Modelo de visión simulado: devuelve `answer` y guarda lo que recibió."""
    got = {"answer": {"es_producto": True, "busqueda": "canilla cocina negra", "descripcion": "Una canilla negra",
                      "confianza": "alta"}, "jpeg": None}

    def fake(system, jpeg):
        got["jpeg"] = jpeg
        return "```json\n" + json.dumps(got["answer"]) + "\n```"      # como lo devuelven algunos modelos
    monkeypatch.setattr(settings, "vision_provider", "ollama")
    monkeypatch.setattr(settings, "vision_model", "vision-test")
    monkeypatch.setattr(vision, "_ollama", fake)
    # El contador por IP es compartido entre pruebas (mismo cliente de test): sin tope acá.
    monkeypatch.setattr(settings, "vision_per_ip_hour", 10_000)
    return got


def _png(exif: bool = False) -> bytes:
    img = Image.new("RGB", (1600, 1200), "black")
    buf = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "MiCelular"            # Make
        img.save(buf, "JPEG", exif=ex)
    else:
        img.save(buf, "PNG")
    return buf.getvalue()


def test_off_without_vision_model(client, accounts, raw_conn, monkeypatch):
    monkeypatch.setattr(settings, "vision_provider", "")
    shop = _shop(client, accounts, raw_conn, "Fotos Apagadas")
    assert client.get(f"/public/{shop['slug']}/photos").json()["enabled"] is False
    r = client.post(f"/public/{shop['slug']}/photos", content=_png(), headers={"Content-Type": "image/png"})
    assert r.status_code == 404


def test_photo_becomes_a_catalog_search(client, accounts, raw_conn, seen):
    shop = _shop(client, accounts, raw_conn, "Fotos Búsqueda")
    _, conv, tok = _say(client, shop, "hola")
    r = client.post(f"/public/{shop['slug']}/photos?conversation_id={conv}", content=_png(),
                    headers={"Content-Type": "image/png", "X-Conversation-Token": tok})
    assert r.status_code == 200 and r.json()["ok"] and "canilla cocina negra" in r.json()["text"]
    with Image.open(io.BytesIO(seen["jpeg"])) as sent:          # achicada y re-codificada
        assert sent.format == "JPEG" and max(sent.size) <= vision.MAX_SIDE
    j, _, _ = _say(client, shop, r.json()["text"], conv, tok)
    assert "Canilla" in j["reply"] and "$" in j["reply"]            # el precio sale del catálogo


def test_exif_is_stripped():
    out = vision.normalize(_png(exif=True))
    with Image.open(io.BytesIO(out)) as img:
        assert not img.getexif()


def test_rejects_fake_images_and_low_confidence(client, accounts, raw_conn, seen):
    shop = _shop(client, accounts, raw_conn, "Fotos Rechazo")
    url = f"/public/{shop['slug']}/photos"
    assert client.post(url, content=b"<script>no soy una foto</script>", headers={"Content-Type": "image/png"}).status_code == 415
    assert client.post(url, content=_png(), headers={"Content-Type": "application/pdf"}).status_code == 415
    seen["answer"] = {"es_producto": True, "busqueda": "algo", "confianza": "baja"}
    r = client.post(url, content=_png(), headers={"Content-Type": "image/png"}).json()
    assert r["ok"] is False and r["text"] is None and "¿Me contás qué es" in r["reply"]
    seen["answer"] = {"es_producto": False}
    assert client.post(url, content=_png(), headers={"Content-Type": "image/png"}).json()["ok"] is False


def test_other_conversation_and_rate_limit(client, accounts, raw_conn, seen, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "Fotos Límites")
    _, conv, _ = _say(client, shop, "hola")
    r = client.post(f"/public/{shop['slug']}/photos?conversation_id={conv}", content=_png(),
                    headers={"Content-Type": "image/png", "X-Conversation-Token": "ajeno"})
    assert r.status_code == 404
    monkeypatch.setattr(settings, "vision_per_ip_hour", 2)
    codes = [client.post(f"/public/{shop['slug']}/photos", content=_png(),
                         headers={"Content-Type": "image/png", "X-Forwarded-For": "203.0.113.77"}).status_code
             for _ in range(3)]
    assert codes[-1] == 429


def test_photo_usage_counts_in_daily_ai_budget(client, accounts, raw_conn, seen, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "Fotos Uso")

    def fake(system, jpeg):
        from app.domain import ai_usage
        ai_usage.record("vision-test", {"prompt_eval_count": 100, "eval_count": 20})
        return json.dumps(seen["answer"])
    monkeypatch.setattr(vision, "_ollama", fake)
    client.post(f"/public/{shop['slug']}/photos", content=_png(), headers={"Content-Type": "image/png"})
    with raw_conn.cursor() as cur:
        cur.execute("select kind, calls from llm_usage where tenant_id = %s", (shop["tenant"],))
        assert [(r["kind"], r["calls"]) for r in cur.fetchall()] == [("foto", 1)]
    raw_conn.commit()
