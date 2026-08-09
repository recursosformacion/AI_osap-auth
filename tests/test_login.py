"""Tests de login y verificación de email."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import pytest

from application.use_cases.login import LoginUseCase
from application.use_cases.register import RegisterUseCase
from application.use_cases.verify_email import VerifyEmailUseCase
from domain.exceptions import InvalidCredentialsError, InvalidTokenError
from tests.fakes import make_context


async def _registered_email(ctx, email: str = "user@example.com") -> str:
    result = await RegisterUseCase(ctx).execute(
        email=email, password="s3cret-password", ip=None, user_agent=None
    )
    assert result.verification_token is not None
    return result.verification_token


async def test_login_success() -> None:
    ctx, _ = make_context()
    await _registered_email(ctx)
    result = await LoginUseCase(ctx).execute(
        email="user@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    assert result.access_token
    assert result.refresh_token
    assert result.email_verified is False


async def test_login_wrong_password_generic() -> None:
    ctx, _ = make_context()
    await _registered_email(ctx)
    with pytest.raises(InvalidCredentialsError):
        await LoginUseCase(ctx).execute(
            email="user@example.com", password="wrong-password", ip=None, user_agent=None
        )


async def test_login_unknown_email_generic() -> None:
    ctx, _ = make_context()
    with pytest.raises(InvalidCredentialsError):
        await LoginUseCase(ctx).execute(
            email="ghost@example.com", password="whatever-password", ip=None, user_agent=None
        )


async def test_verify_email_activates() -> None:
    ctx, _ = make_context()
    token = await _registered_email(ctx)
    await VerifyEmailUseCase(ctx).execute(token=token, ip=None, user_agent=None)
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    assert user.email_verified is True
    assert user.status.value == "active"


async def test_verify_email_token_single_use() -> None:
    ctx, _ = make_context()
    token = await _registered_email(ctx)
    await VerifyEmailUseCase(ctx).execute(token=token, ip=None, user_agent=None)
    with pytest.raises(InvalidTokenError):
        await VerifyEmailUseCase(ctx).execute(token=token, ip=None, user_agent=None)


async def test_verify_email_bad_token() -> None:
    ctx, _ = make_context()
    await _registered_email(ctx)
    with pytest.raises(InvalidTokenError):
        await VerifyEmailUseCase(ctx).execute(token="bad-token", ip=None, user_agent=None)
