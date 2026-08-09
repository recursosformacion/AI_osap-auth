"""Tests de recuperación de contraseña."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from application.use_cases.login import LoginUseCase
from application.use_cases.password_reset import (
    ConfirmPasswordResetUseCase,
    RequestPasswordResetUseCase,
)
from application.use_cases.register import RegisterUseCase
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.exceptions import InvalidCredentialsError, InvalidTokenError
from tests.fakes import make_context


async def test_request_reset_generic_for_unknown() -> None:
    ctx, _ = make_context()
    # No debe lanzar ni crear tokens para una cuenta inexistente.
    await RequestPasswordResetUseCase(ctx).execute(
        email="ghost@example.com", ip=None, user_agent=None
    )
    assert all(t.purpose != TokenPurpose.RESET_PASSWORD for t in ctx.tokens._tokens)  # noqa: SLF001


async def test_reset_confirm_with_bad_token_rejected() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    with pytest.raises(InvalidTokenError):
        await ConfirmPasswordResetUseCase(ctx).execute(
            token="not-the-raw-token", new_password="new-s3cret-password", ip=None, user_agent=None
        )


async def test_reset_revokes_sessions_and_clears_password() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    await LoginUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001

    # Creamos un token de reset válido directamente (el raw es el que viajaría por email).
    raw = "valid-raw-reset-token"
    valid = TokenRecord.new(
        user_id=user.id,
        purpose=TokenPurpose.RESET_PASSWORD,
        token_hash=ctx.token_hasher.hash(raw),
        ttl_hours=1,
    )
    valid.expires_at = datetime.now(UTC) + timedelta(minutes=30)
    await ctx.tokens.save(valid)

    await ConfirmPasswordResetUseCase(ctx).execute(
        token=raw, new_password="brand-new-password", ip=None, user_agent=None
    )

    # Todas las sesiones revocadas.
    sessions = await ctx.sessions.list_for_user(user.id)
    assert sessions and all(s.revoked_at is not None for s in sessions)

    # La contraseña anterior ya no es válida.
    with pytest.raises(InvalidCredentialsError):
        await LoginUseCase(ctx).execute(
            email="u@example.com", password="s3cret-password", ip=None, user_agent=None
        )
