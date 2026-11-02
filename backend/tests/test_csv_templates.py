"""Las plantillas CSV que descarga el panel (una por rubro) se importan sin errores."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, bearer

SOURCE = Path(__file__).resolve().parents[2] / "web" / "src" / "pages" / "Catalog.tsx"


def _templates() -> dict[str, str]:
    src = SOURCE.read_text(encoding="utf-8")
    cols = re.search(r'const COLS = "([^"]*)";', src).group(1)
    out = {}
    for name, body in re.findall(r'^  (\w+): COLS \+\n((?:    "[^"]*"(?: \+)?,?\n)+)', src, re.M):
        rows = "".join(re.findall(r'"([^"]*)"', body))
        out[name] = (cols + rows).replace("\\n", "\n")
    return out


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_every_rubro_template_imports_cleanly(accounts):
    templates = _templates()
    assert set(templates) == {"ferreteria", "ropa", "gastronomia", "generico"}
    client = TestClient(app)
    for name, csv in templates.items():
        uid, _ = accounts(f"Plantilla {name}")
        r = client.post("/app/catalog/import", headers=bearer(uid), json={"csv": csv})
        assert r.status_code == 200 and r.json()["errors"] == [], (name, r.text)
        assert r.json()["created"] == csv.count("\n") - 1, name
