"""Tests de los correos transaccionales de identidad (verificación y reset)."""

from __future__ import annotations

from typing import Literal

from application.context import AuthContext
from application.use_cases.password_reset import RequestPasswordResetUseCase
from application.use_cases.register import RegisterUseCase
from application.use_cases.verify_email import ResendVerificationUseCase
from domain.ports.email import EmailMessage
from infrastructure.email.fake_email_sender import FakeEmailSender
from infrastructure.email.smtp_email_sender import SmtpEmailSender, SmtpSettings
from tests.fakes import make_context


def _sender(ctx: AuthContext) -> FakeEmailSender:
    assert isinstance(ctx.email_sender, FakeEmailSender)
    return ctx.email_sender


async def test_register_envia_verificacion() -> None:
    ctx, _ = make_context()
    result = await RegisterUseCase(ctx).execute(
        email="nuevo@example.com", password="s3cret-password", ip="127.0.0.1", user_agent="t"
    )
    sent = _sender(ctx).sent
    assert len(sent) == 1
    assert sent[0].to == "nuevo@example.com"
    assert result.verification_token is not None
    assert f"/auth/verify-email?token={result.verification_token}" in sent[0].body


async def test_resend_envia_otra_verificacion() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="nuevo@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    sender = _sender(ctx)
    sender.sent.clear()
    await ResendVerificationUseCase(ctx).execute(
        email="nuevo@example.com", ip=None, user_agent=None
    )
    assert len(sender.sent) == 1
    assert "/auth/verify-email?token=" in sender.sent[0].body


async def test_password_reset_envia_enlace() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="nuevo@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    sender = _sender(ctx)
    sender.sent.clear()
    await RequestPasswordResetUseCase(ctx).execute(
        email="nuevo@example.com", ip=None, user_agent=None
    )
    assert len(sender.sent) == 1
    assert "/auth/reset-password?token=" in sender.sent[0].body


async def test_password_reset_email_desconocido_no_envia() -> None:
    ctx, _ = make_context()
    await RequestPasswordResetUseCase(ctx).execute(
        email="nadie@example.com", ip=None, user_agent=None
    )
    assert _sender(ctx).sent == []


def test_smtp_sender_envia_en_modo_ssl(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeSmtp:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> _FakeSmtp:
            return self

        def __exit__(self, *args: object) -> Literal[False]:
            return False

        def ehlo(self) -> None:
            pass

        def login(self, user: str, password: str) -> None:
            captured["login"] = (user, password)

        def send_message(self, message: object) -> None:
            captured["message"] = message

    monkeypatch.setattr(
        "infrastructure.email.smtp_email_sender.smtplib.SMTP_SSL", _FakeSmtp
    )
    sender = SmtpEmailSender(
        SmtpSettings(
            host="smtp.test",
            port=465,
            username="user",
            password="secret",
            from_address="no-reply@test",
        )
    )
    assert sender.send(EmailMessage(to="a@b.c", subject="Alta", body="Cuerpo")) is True
    assert captured["login"] == ("user", "secret")
    assert captured["message"]["To"] == "a@b.c"  # type: ignore[index]
