"""Entidad de usuario.

El email NO se guarda en claro: solo `email_lookup` (HMAC para localizar) y
`email_cipher` (AEAD para mostrar). Entre aplicaciones solo viaja `id` (UUID).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

DEFAULT_ROLES: tuple[str, ...] = ("user",)
ALL_ROLES: tuple[str, ...] = ("user", "moderator", "admin")


class UserStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class User:
    """Usuario de identidad de OSAP."""

    def __init__(
        self,
        *,
        id: uuid.UUID,
        email_lookup: str,
        email_cipher: bytes,
        password_hash: str,
        status: UserStatus,
        roles: list[str],
        key_version: int,
        name: str | None = None,
        email_verified_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.email_lookup = email_lookup
        self.email_cipher = email_cipher
        self.password_hash = password_hash
        self.status = status
        self.roles = roles or list(DEFAULT_ROLES)
        self.key_version = key_version
        self.name = name
        self.email_verified_at = email_verified_at
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    @classmethod
    def new(
        cls,
        *,
        email_lookup: str,
        email_cipher: bytes,
        password_hash: str,
        key_version: int,
        roles: list[str] | None = None,
        name: str | None = None,
    ) -> User:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            email_lookup=email_lookup,
            email_cipher=email_cipher,
            password_hash=password_hash,
            status=UserStatus.PENDING_VERIFICATION,
            roles=roles or list(DEFAULT_ROLES),
            key_version=key_version,
            name=name,
            created_at=now,
            updated_at=now,
        )
