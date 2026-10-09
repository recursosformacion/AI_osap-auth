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
from domain.exceptions import (
    EmailTakenError,
    InvalidNicknameError,
    NicknameTakenError,
    UserNotFoundError,
)
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


async def test_admin_update_nickname() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    updated = await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
        nickname="Maestro", actor="admin", ip=None, user_agent=None,
    )
    assert updated["nickname"] == "Maestro"
    user = await ctx.users.get_by_id(uuid.UUID(created["user_id"]))
    assert user is not None and user.nickname_norm == "maestro"


async def test_admin_update_nickname_duplicado_rejected() -> None:
    ctx, _ = make_context()
    a = await AdminCreateUserUseCase(ctx).execute(
        email="a@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    b = await AdminCreateUserUseCase(ctx).execute(
        email="b@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(a["user_id"]), name=None, roles=None, status=None,
        nickname="cosmos", actor="admin", ip=None, user_agent=None,
    )
    with pytest.raises(NicknameTakenError):
        await AdminUpdateUserUseCase(ctx).execute(
            user_id=uuid.UUID(b["user_id"]), name=None, roles=None, status=None,
            nickname="Cosmos", actor="admin", ip=None, user_agent=None,
        )


async def test_admin_update_nickname_invalido_rejected() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    with pytest.raises(InvalidNicknameError):
        await AdminUpdateUserUseCase(ctx).execute(
            user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
            nickname="x", actor="admin", ip=None, user_agent=None,
        )


async def test_admin_clear_nickname() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
        nickname="temporal", actor="admin", ip=None, user_agent=None,
    )
    updated = await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
        nickname="  ", actor="admin", ip=None, user_agent=None,
    )
    assert updated["nickname"] is None
    user = await ctx.users.get_by_id(uuid.UUID(created["user_id"]))
    assert user is not None and user.nickname_norm is None


async def test_admin_deshabilitar_revoca_sesiones() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    await LoginUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    sessions_before = await ctx.sessions.list_for_user(user.id)
    assert sessions_before

    await AdminUpdateUserUseCase(ctx).execute(
        user_id=user.id, name=None, roles=None, status="disabled",
        actor="admin", ip=None, user_agent=None,
    )

    sessions_after = await ctx.sessions.list_for_user(user.id)
    assert sessions_after
    assert all(s.revoked_at is not None for s in sessions_after)


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
    # Anonimización: se libera el email (nuevo lookup) y se borra el email cifrado.
    assert user.email_lookup == f"deleted-{user.id}"
    assert user.email_cipher == b""
    for s in await ctx.sessions.list_for_user(user.id):
        assert s.revoked_at is not None
    # El evento user.deleted se publica (osap-api anonimiza votos).
    assert any(e["user_id"] == str(user.id) for e in ctx.events.events)


async def test_admin_notify_recognition_envia_email() -> None:
    from application.use_cases.notify_recognition import NotifyRecognitionUseCase

    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    await NotifyRecognitionUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]),
        recognition_type="founder",
        action="granted",
        project="omr",
    )
    avisos = [m for m in ctx.email_sender.sent if m.context.get("kind") == "recognition"]
    assert len(avisos) == 1
    assert avisos[0].to == "u@example.com"
    assert "founder" in avisos[0].subject


async def test_admin_nickname_envia_aviso() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
        nickname="Maestro", actor="admin", ip=None, user_agent=None,
    )
    avisos = [m for m in ctx.email_sender.sent if m.context.get("kind") == "nickname_assigned"]
    assert len(avisos) == 1
    assert avisos[0].to == "u@example.com"
    assert "Maestro" in avisos[0].subject


async def test_admin_nickname_igual_no_repite_aviso() -> None:
    ctx, _ = make_context()
    created = await AdminCreateUserUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", roles=["user"],
        actor="admin", ip=None, user_agent=None,
    )
    await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
        nickname="Maestro", actor="admin", ip=None, user_agent=None,
    )
    antes = len(ctx.email_sender.sent)
    await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(created["user_id"]), name=None, roles=None, status=None,
        nickname="Maestro", actor="admin", ip=None, user_agent=None,
    )
    assert len(ctx.email_sender.sent) == antes


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
