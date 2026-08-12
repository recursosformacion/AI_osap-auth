"""Cuenta vinculada a un proveedor social externo (Google, GitHub, …)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


class ProviderAccount:
    """Vínculo entre un proveedor externo y un usuario local de osap-auth."""

    def __init__(
        self,
        *,
        id: uuid.UUID,
        provider: str,
        provider_sub: str,
        user_id: uuid.UUID,
        email: str | None,
        name: str | None,
        linked_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.provider = provider
        self.provider_sub = provider_sub
        self.user_id = user_id
        self.email = email
        self.name = name
        self.linked_at = linked_at

    @classmethod
    def new(
        cls,
        *,
        provider: str,
        provider_sub: str,
        user_id: uuid.UUID,
        email: str | None = None,
        name: str | None = None,
    ) -> ProviderAccount:
        return cls(
            id=uuid.uuid4(),
            provider=provider,
            provider_sub=provider_sub,
            user_id=user_id,
            email=email,
            name=name,
            linked_at=datetime.now(UTC),
        )
