"""Tests de refresh: rotación y detección de reutilización."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import pytest

from application.use_cases.login import LoginUseCase
from application.use_cases.refresh import RefreshUseCase
from application.use_cases.register import RegisterUseCase
from domain.exceptions import InvalidTokenError, TokenReuseDetectedError
from tests.fakes import make_context


async def _login(ctx) -> str:
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    result = await LoginUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    return result.refresh_token


async def test_refresh_rotates_and_reuse_detected() -> None:
    ctx, _ = make_context()
    first_refresh = await _login(ctx)

    refreshed = await RefreshUseCase(ctx).execute(
        refresh_token=first_refresh, ip=None, user_agent=None
    )
    assert refreshed.access_token
    assert refreshed.refresh_token != first_refresh

    # Reutilizar el refresh ya rotado debe detectarse como reuso y revocar sesiones.
    with pytest.raises(TokenReuseDetectedError):
        await RefreshUseCase(ctx).execute(refresh_token=first_refresh, ip=None, user_agent=None)

    # Todas las sesiones del usuario quedaron revocadas.
    sessions = await ctx.sessions.list_for_user(
        next(iter(ctx.users._users.values())).id  # noqa: SLF001
    )
    assert all(s.revoked_at is not None for s in sessions)


async def test_refresh_invalid_token() -> None:
    ctx, _ = make_context()
    with pytest.raises(InvalidTokenError):
        await RefreshUseCase(ctx).execute(refresh_token="garbage", ip=None, user_agent=None)
