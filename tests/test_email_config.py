"""Tests de A4: SMTP obligatorio en producción (FakeEmailSender no es válido).

En development/test el remitente falso se permite explícitamente; en producción la falta
de configuración SMTP o un sender falso deben impedir el arranque.
"""

from __future__ import annotations

import pytest

from infrastructure.config import Settings
from infrastructure.container import build_email_sender
from infrastructure.email.fake_email_sender import FakeEmailSender
from infrastructure.email.smtp_email_sender import SmtpEmailSender

_SMTP_ENV = (
    "OSAP_AUTH_SMTP_HOST",
    "OSAP_AUTH_SMTP_PORT",
    "OSAP_AUTH_SMTP_USERNAME",
    "OSAP_AUTH_SMTP_USER",
    "OSAP_AUTH_SMTP_PASSWORD",
    "OSAP_AUTH_SMTP_FROM",
    "OSAP_AUTH_SMTP_SSL",
    "OSAP_AUTH_SMTP_STARTTLS",
)


@pytest.fixture(autouse=True)
def _clear_smtp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _SMTP_ENV:
        monkeypatch.delenv(name, raising=False)


def test_produccion_sin_smtp_no_arranca() -> None:
    with pytest.raises(RuntimeError):
        build_email_sender(Settings(env="production"))


def test_development_sin_smtp_usa_fake() -> None:
    assert isinstance(build_email_sender(Settings(env="development")), FakeEmailSender)


def test_test_sin_smtp_usa_fake() -> None:
    assert isinstance(build_email_sender(Settings(env="test")), FakeEmailSender)


def test_produccion_con_smtp_usa_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_AUTH_SMTP_HOST", "smtp.example.com")
    assert isinstance(build_email_sender(Settings(env="production")), SmtpEmailSender)
