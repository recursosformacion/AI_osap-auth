"""Entidad de sesión revocable de osap-auth."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from domain.util import ensure_utc


class Session:
    """Sesión activa de usuario. Su `id` es el `jti` del access token."""

    def __init__(
        self,
        *,
        id: uuid.UUID,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        refresh_expires_at: datetime,
        created_at: datetime,
        last_used_at: datetime,
        revoked_at: datetime | None = None,
        previous_refresh_token_hash: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.refresh_token_hash = refresh_token_hash
        self.previous_refresh_token_hash = previous_refresh_token_hash
        self.refresh_expires_at = refresh_expires_at
        self.created_at = created_at
        self.last_used_at = last_used_at
        self.revoked_at = revoked_at
        self.ip = ip
        self.user_agent = user_agent
        self.device_label = device_label

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and ensure_utc(self.refresh_expires_at) > datetime.now(UTC)

    def revoke(self) -> None:
        self.revoked_at = datetime.now(UTC)

    def touch(self) -> None:
        self.last_used_at = datetime.now(UTC)

    @classmethod
    def new(
        cls,
        *,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        refresh_ttl_seconds: int,
        ip: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> Session:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            refresh_expires_at=now + timedelta(seconds=refresh_ttl_seconds),
            created_at=now,
            last_used_at=now,
            ip=ip,
            user_agent=user_agent,
            device_label=device_label,
        )
