"""Casos de uso de administración de usuarios (solo rol admin)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from application.audit import audit
from application.context import AuthContext
from domain.entities.user import ALL_ROLES, User, UserStatus
from domain.exceptions import EmailTakenError, UserNotFoundError
from domain.services.email_utils import normalize_email, validate_password


def public_user(ctx: AuthContext, user: User) -> dict[str, Any]:
    email = ctx.email_protector.decrypt(user.email_cipher) if user.email_cipher else ""
    return {
        "user_id": str(user.id),
        "email": email,
        "name": user.name,
        "roles": user.roles,
        "email_verified": user.email_verified,
        "status": user.status.value,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _validate_roles(roles: list[str]) -> list[str]:
    roles = list(dict.fromkeys(roles))
    invalid = [r for r in roles if r not in ALL_ROLES]
    if invalid:
        raise ValueError(f"roles inválidos: {invalid}")
    return roles or ["user"]


class AdminListUsersUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self) -> list[dict[str, Any]]:
        return [public_user(self._ctx, u) for u in await self._ctx.users.list_all()
                if u.status != UserStatus.DELETED]


class AdminGetUserUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, user_id: uuid.UUID) -> dict[str, Any]:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None or user.status == UserStatus.DELETED:
            raise UserNotFoundError("usuario no encontrado")
        return public_user(self._ctx, user)


class AdminCreateUserUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, email: str, password: str, roles: list[str],
        actor: str, ip: str | None, user_agent: str | None,
        name: str | None = None,
    ) -> dict[str, Any]:
        validate_password(password)
        normalized = normalize_email(email)
        lookup = self._ctx.email_protector.lookup(normalized)
        if await self._ctx.users.exists(lookup):
            raise EmailTakenError("el email ya está en uso")

        roles = _validate_roles(roles)
        user = User(
            id=uuid.uuid4(),
            email_lookup=lookup,
            email_cipher=self._ctx.email_protector.encrypt(normalized),
            password_hash=self._ctx.password_hasher.hash(password),
            status=UserStatus.ACTIVE,
            roles=roles,
            key_version=self._ctx.settings.key_version,
            name=(name or "").strip() or None,
            email_verified_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await self._ctx.users.save(user)
        await audit(
            self._ctx, event_type="user.admin.created", actor=actor,
            subject=str(user.id), ip=ip, user_agent=user_agent, outcome="success",
            context={"roles": roles},
        )
        return public_user(self._ctx, user)


class AdminUpdateUserUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, user_id: uuid.UUID, name: str | None, roles: list[str] | None,
        status: str | None, actor: str, ip: str | None, user_agent: str | None,
    ) -> dict[str, Any]:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None or user.status == UserStatus.DELETED:
            raise UserNotFoundError("usuario no encontrado")

        if name is not None:
            user.name = name.strip() or None
        if roles is not None:
            user.roles = _validate_roles(roles)
        if status is not None:
            user.status = UserStatus(status)
        user.touch()
        await self._ctx.users.save(user)
        await audit(
            self._ctx, event_type="role.changed", actor=actor,
            subject=str(user.id), ip=ip, user_agent=user_agent, outcome="success",
            context={"roles": user.roles, "status": user.status.value},
        )
        return public_user(self._ctx, user)


class AdminDeleteUserUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, user_id: uuid.UUID, actor: str, ip: str | None, user_agent: str | None
    ) -> None:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            return
        await self._ctx.sessions.revoke_all_for_user(user.id)
        user.status = UserStatus.DELETED
        user.email_verified_at = None
        user.email_cipher = b""
        user.email_lookup = f"deleted-{user.id}"
        user.password_hash = ""
        user.touch()
        await self._ctx.users.save(user)
        deleted_at = datetime.now(UTC).isoformat()
        await audit(
            self._ctx, event_type="user.deleted", actor=actor,
            subject=str(user.id), ip=ip, user_agent=user_agent, outcome="success",
            context={"deleted_at": deleted_at},
        )
        await self._ctx.events.publish_user_deleted(user.id, deleted_at)
