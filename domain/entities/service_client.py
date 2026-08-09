"""Cliente de servicio (machine-to-machine) de osap-auth."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

SCOPES: tuple[str, ...] = (
    "api:read",
    "storage:read",
    "storage:write",
    "storage:admin",
    "auth:admin",
    "user.deleted:subscribe",
)

VALID_SCOPES: set[str] = set(SCOPES)


class ServiceClient:
    """Cliente OAuth2 `client_credentials`. El secreto solo se guarda hasheado."""

    def __init__(
        self,
        *,
        client_id: uuid.UUID,
        client_secret_hash: str,
        scopes: list[str],
        enabled: bool,
        created_at: datetime | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret_hash = client_secret_hash
        self.scopes = scopes
        self.enabled = enabled
        self.created_at = created_at

    @classmethod
    def new(cls, *, client_secret_hash: str, scopes: list[str]) -> ServiceClient:
        return cls(
            client_id=uuid.uuid4(),
            client_secret_hash=client_secret_hash,
            scopes=scopes,
            enabled=True,
            created_at=datetime.now(UTC),
        )
