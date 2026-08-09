"""Tests de administración de usuarios (CRUD, solo admin)."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import uuid

import pytest

from application.use_cases.admin_users import (
    AdminCreateUserUseCase,
    AdminDeleteUserUseCase,
    AdminGetUserUseCase,
    AdminListUsersUseCase,
    AdminUpdateUserUseCase,
)
from application.use_cases.login import LoginUseCase
from application.use_cases.register import RegisterUseCase
from domain.entities.user import UserStatus
from domain.exceptions import EmailTakenError, UserNotFoundError
from tests.fakes import make_context


async def test_admin_create_user_active_and_verified() -> None:
    ctx, _ = make_context()
    result = await AdminCreateUserUseCase(ctx).execute(
        email="new@example.com", password="s3cret-password", name="Nuevo", roles=["moderator"],
        actor="admin-id", ip=None, user_agent=None,
    )
    assert result["status"] == "active"
    assert result["email_verified"] is True
    assert result["roles"] == ["moderator"]
    assert result["name"] == "Nuevo"
    # El email no se guarda en claro.
    user = await ctx.users.get_by_id(uuid.UUID(result["user_id"]))
    assert user is not None and user.email_lookup != "new@example.com"


async def test_admin_create_duplicate_email_rejected() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="a@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    with pytest.raises(EmailTakenError):
        await AdminCreateUserUseCase(ctx).execute(
            email="a@example.com", password="s3cret-password", roles=["user"],
            actor="admin", ip=None, user_agent=None,
        )


async def test_admin_update_roles_and_status() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    updated = await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name="Renombrado", roles=["user", "admin"],
        status="active", actor="admin", ip=None, user_agent=None,
    )
    assert updated["roles"] == ["user", "admin"]
    assert updated["name"] == "Renombrado"


async def test_admin_get_missing_user_404() -> None:
    ctx, _ = make_context()
    with pytest.raises(UserNotFoundError):
        await AdminGetUserUseCase(ctx).execute(user_id=uuid.uuid4())


async def test_admin_delete_soft_deletes_and_revokes() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    await LoginUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    user = next(iter(ctx.users._users.values()))
    await AdminDeleteUserUseCase(ctx).execute(
        user_id=user.id, actor="admin", ip=None, user_agent=None
    )
    assert user.status == UserStatus.DELETED
    assert user.password_hash == ""
    for s in await ctx.sessions.list_for_user(user.id):
        assert s.revoked_at is not None
    # El evento user.deleted se publica (osap-api anonimiza votos).
    assert any(e["user_id"] == str(user.id) for e in ctx.events.events)


async def test_admin_list_excludes_deleted() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="a@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    await AdminDeleteUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), actor="admin", ip=None, user_agent=None
    )
    remaining = await AdminListUsersUseCase(ctx).execute()
    assert all(u["user_id"] != created["user_id"] for u in remaining)
