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
    "support:ingest",
)

VALID_SCOPES: set[str] = set(SCOPES)


class ServiceClient:
    """Cliente OAuth2 `client_credentials`. El secreto solo se guarda hasheado.

    `allowed_audiences`: audiencias objetivo que el cliente puede solicitar al emitir un
    service token. Vacía = solo la audiencia global por defecto (sin override). El patrón
    es el mismo que el de `scopes`: intersección entre lo solicitado y lo permitido.
    """

    def __init__(
        self,
        *,
        client_id: uuid.UUID,
        client_secret_hash: str,
        scopes: list[str],
        enabled: bool,
        allowed_audiences: list[str] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret_hash = client_secret_hash
        self.scopes = scopes
        self.enabled = enabled
        self.allowed_audiences = allowed_audiences or []
        self.created_at = created_at

    @classmethod
    def new(
        cls,
        *,
        client_secret_hash: str,
        scopes: list[str],
        allowed_audiences: list[str] | None = None,
    ) -> ServiceClient:
        return cls(
            client_id=uuid.uuid4(),
            client_secret_hash=client_secret_hash,
            scopes=scopes,
            enabled=True,
            allowed_audiences=allowed_audiences,
            created_at=datetime.now(UTC),
        )

    def allows_audience(self, audience: str) -> bool:
        """Cierto si el cliente puede pedir esta audiencia al emitir un token."""
        return audience in self.allowed_audiences
