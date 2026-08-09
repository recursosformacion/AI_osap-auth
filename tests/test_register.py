"""Tests del caso de uso de registro."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import pytest

from application.use_cases.register import RegisterUseCase
from domain.exceptions import InvalidEmailError, RateLimitedError, WeakPasswordError
from tests.fakes import make_context


async def test_register_creates_pending_user() -> None:
    ctx, _ = make_context()
    result = await RegisterUseCase(ctx).execute(
        email="user@example.com", password="s3cret-password", ip="127.0.0.1", user_agent="test"
    )
    assert result.created is True
    assert result.verification_token is not None
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    assert user.status.value == "pending_verification"
    assert user.email_verified is False


async def test_register_email_not_stored_in_plain() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="user@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    user = list(ctx.users._users.values())[0]  # noqa: SLF001
    assert user.email_cipher != b"user@example.com"
    assert user.email_lookup != "user@example.com"
    # El email se puede recuperar cifrado.
    assert ctx.email_protector.decrypt(user.email_cipher) == "user@example.com"


async def test_register_duplicate_is_generic() -> None:
    ctx, _ = make_context()
    uc = RegisterUseCase(ctx)
    await uc.execute(email="a@example.com", password="s3cret-password", ip=None, user_agent=None)
    # Repetir no revela existencia: created=False, misma respuesta genérica.
    result = await uc.execute(
        email="a@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    assert result.created is False
    assert result.verification_token is None
    assert len(ctx.users._users) == 1  # noqa: SLF001


async def test_register_weak_password_rejected() -> None:
    ctx, _ = make_context()
    with pytest.raises(WeakPasswordError):
        await RegisterUseCase(ctx).execute(
            email="a@example.com", password="short", ip=None, user_agent=None
        )


async def test_register_invalid_email_rejected() -> None:
    ctx, _ = make_context()
    with pytest.raises(InvalidEmailError):
        await RegisterUseCase(ctx).execute(
            email="not-an-email", password="s3cret-password", ip=None, user_agent=None
        )


async def test_register_rate_limited() -> None:
    ctx, _ = make_context()
    ctx.settings.register_per_minute = 1
    uc = RegisterUseCase(ctx)
    await uc.execute(
        email="a@example.com", password="s3cret-password", ip="1.1.1.1", user_agent=None
    )
    with pytest.raises(RateLimitedError):
        await uc.execute(
            email="b@example.com", password="s3cret-password", ip="1.1.1.1", user_agent=None
        )
