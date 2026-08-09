"""Token de un solo uso de osap-auth (verificación de email / recuperación)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from domain.util import ensure_utc


class TokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"
    CHANGE_EMAIL = "change_email"


class TokenRecord:
    """Registro de un token opaco de un solo uso. Solo se persiste su hash."""

    def __init__(
        self,
        *,
        id: uuid.UUID,
        user_id: uuid.UUID,
        purpose: TokenPurpose,
        token_hash: str,
        expires_at: datetime,
        used_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.purpose = purpose
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.used_at = used_at
        self.created_at = created_at

    @property
    def is_expired(self) -> bool:
        return ensure_utc(self.expires_at) <= datetime.now(UTC)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def mark_used(self) -> None:
        self.used_at = datetime.now(UTC)

    @classmethod
    def new(
        cls,
        *,
        user_id: uuid.UUID,
        purpose: TokenPurpose,
        token_hash: str,
        ttl_hours: float,
    ) -> TokenRecord:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=ttl_hours),
            created_at=now,
        )
