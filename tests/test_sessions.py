"""Tests de sesiones (logout, logout-all, listado, revocación individual)."""

from __future__ import annotations

import uuid

from application.use_cases.login import LoginUseCase
from application.use_cases.register import RegisterUseCase
from application.use_cases.sessions import (
    ListSessionsUseCase,
    LogoutAllUseCase,
    RevokeSessionUseCase,
)
from domain.exceptions import SessionNotFoundError
from tests.fakes import make_context


async def _make_user_and_login(ctx) -> uuid.UUID:
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    await LoginUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    return next(iter(ctx.users._users.values())).id  # noqa: SLF001


async def test_list_sessions() -> None:
    ctx, _ = make_context()
    user_id = await _make_user_and_login(ctx)
    rows = await ListSessionsUseCase(ctx).execute(user_id=user_id)
    assert len(rows) == 1
    assert rows[0]["revoked"] is False


async def test_revoke_individual_session() -> None:
    ctx, _ = make_context()
    user_id = await _make_user_and_login(ctx)
    session = (await ctx.sessions.list_for_user(user_id))[0]
    await RevokeSessionUseCase(ctx).execute(
        session_id=session.id, user_id=user_id, ip=None, user_agent=None
    )
    assert (await ctx.sessions.get_by_id(session.id)).revoked_at is not None  # type: ignore[union-attr]


async def test_revoke_foreign_session_rejected() -> None:
    ctx, _ = make_context()
    user_id = await _make_user_and_login(ctx)
    session = (await ctx.sessions.list_for_user(user_id))[0]
    try:
        await RevokeSessionUseCase(ctx).execute(
            session_id=session.id, user_id=uuid.uuid4(), ip=None, user_agent=None
        )
        raise AssertionError("debería haber lanzado SessionNotFoundError")
    except SessionNotFoundError:
        pass


async def test_logout_all_revokes_all() -> None:
    ctx, _ = make_context()
    user_id = await _make_user_and_login(ctx)
    await LogoutAllUseCase(ctx).execute(user_id=user_id, ip=None, user_agent=None)
    for s in await ctx.sessions.list_for_user(user_id):
        assert s.revoked_at is not None
