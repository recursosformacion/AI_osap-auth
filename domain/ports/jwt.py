"""Emisor/validador de tokens JWT y JWKS de osap-auth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from domain.entities.service_client import ServiceClient


class TokenProvider(ABC):
    """Emite y valida access tokens (usuario) y service tokens (máquina a máquina)."""

    @abstractmethod
    def issue_access_token(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        roles: list[str],
        email_verified: bool,
        scope: str,
        ttl_seconds: int,
    ) -> str: ...

    @abstractmethod
    def issue_service_token(
        self,
        *,
        client: ServiceClient,
        scope: str,
        ttl_seconds: int,
    ) -> str: ...

    @abstractmethod
    def verify_access_token(self, token: str, *, expected_audience: str) -> dict[str, Any]:
        """Valida firma/iss/aud/exp/iat y devuelve los claims (rechaza si PII)."""

    @abstractmethod
    def verify_service_token(self, token: str, *, expected_audience: str) -> dict[str, Any]: ...

    @abstractmethod
    def jwks(self) -> dict[str, Any]: ...
