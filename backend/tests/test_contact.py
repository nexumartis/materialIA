"""Captura de contacto del cliente (teléfono y email) en los requisitos.
Misma postura de privacidad que el resto: la auditoría NO guarda estos datos
(ver test_chat.test_audit_event_has_no_sensitive_content)."""
from __future__ import annotations

from app.agent import orchestrator
from app.agent.llm_adapter import _parse_requirements

from conftest import TENANT_A


def test_parse_extracts_email():
    req, _, _ = _parse_requirements("mi correo es Juan.Perez@mail.com")
    assert req.get("customer_email") == "Juan.Perez@mail.com"


def test_parse_extracts_phone():
    req, _, _ = _parse_requirements("llamame al 11-5555-1234")
    assert req.get("customer_phone") == "11-5555-1234"


def test_phone_not_confused_with_measures():
    req, _, _ = _parse_requirements("una mampara corrediza de 1,60 x 1,90")
    assert "customer_phone" not in req


def test_chat_persists_contact_in_requirements():
    r = orchestrator.handle_chat(
        TENANT_A,
        "Quiero una mampara corrediza negra de 1,60 x 1,90 en Tigre. "
        "Mi tel 11-5555-1234, mail juan@mail.com",
    )
    assert r.collected_requirements.get("customer_phone") == "11-5555-1234"
    assert r.collected_requirements.get("customer_email") == "juan@mail.com"
