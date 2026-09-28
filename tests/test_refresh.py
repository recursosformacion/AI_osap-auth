"""Tests de refresh: rotación y detección de reutilización."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from application.use_cases.login import LoginUseCase
from application.use_cases.refresh import RefreshUseCase
from application.use_cases.register import RegisterUseCase
from domain.entities.session import Session
from domain.entities.user import UserStatus
from domain.exceptions import InvalidTokenError, TokenReuseDetectedError
from tests.fakes import FakeSessionRepository, make_context


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


@pytest.mark.parametrize("status", [UserStatus.DISABLED, UserStatus.DELETED])
async def test_refresh_rechazado_si_usuario_no_activo(status: UserStatus) -> None:
    ctx, _ = make_context()
    first_refresh = await _login(ctx)
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    user.status = status
    await ctx.users.save(user)

    with pytest.raises(InvalidTokenError):
        await RefreshUseCase(ctx).execute(refresh_token=first_refresh, ip=None, user_agent=None)


async def test_consume_and_rotate_es_atomico() -> None:
    ctx, _ = make_context()
    token = await _login(ctx)
    session = await ctx.sessions.get_by_refresh_hash(ctx.token_hasher.hash(token))
    assert session is not None
    expected = session.refresh_token_hash
    new_exp = datetime.now(UTC) + timedelta(seconds=3600)

    # Hash esperado que no coincide: no consume.
    assert await ctx.sessions.consume_and_rotate(session.id, "otro-hash", "n1", new_exp) is False
    # Primer consumo: rota.
    assert await ctx.sessions.consume_and_rotate(session.id, expected, "n1", new_exp) is True
    # Segundo consumo del mismo hash (ya rotado): rechazado.
    assert await ctx.sessions.consume_and_rotate(session.id, expected, "n2", new_exp) is False


class _BarrierSessionRepository(FakeSessionRepository):
    """Fuerza que dos lecturas de refresh ocurran antes de que ninguna rote."""

    def __init__(self) -> None:
        super().__init__()
        self._readers = 0
        self._both_read = asyncio.Event()

    async def get_by_refresh_hash(self, refresh_token_hash: str) -> Session | None:
        result = await super().get_by_refresh_hash(refresh_token_hash)
        if result is not None:
            self._readers += 1
            if self._readers >= 2:
                self._both_read.set()
            await self._both_read.wait()
        return result


async def test_refresh_doble_consumo_concurrente_solo_uno_gana() -> None:
    sessions = _BarrierSessionRepository()
    ctx, _ = make_context(sessions=sessions)
    token = await _login(ctx)

    results = await asyncio.gather(
        RefreshUseCase(ctx).execute(refresh_token=token, ip=None, user_agent=None),
        RefreshUseCase(ctx).execute(refresh_token=token, ip=None, user_agent=None),
        return_exceptions=True,
    )
    ok = [r for r in results if not isinstance(r, BaseException)]
    errs = [r for r in results if isinstance(r, BaseException)]
    assert len(ok) == 1
    assert len(errs) == 1
    assert isinstance(errs[0], TokenReuseDetectedError)

    # Ante el doble consumo, todas las sesiones del usuario quedan revocadas.
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    for session in await ctx.sessions.list_for_user(user.id):
        assert session.revoked_at is not None
