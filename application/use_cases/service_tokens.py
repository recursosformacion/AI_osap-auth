"""Caso de uso: emisión de tokens de servicio (client_credentials)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from application.audit import audit
from application.context import AuthContext
from domain.entities.service_client import VALID_SCOPES
from domain.exceptions import (
    ServiceClientDisabledError,
    ServiceClientNotFoundError,
)


@dataclass
class ServiceTokenResult:
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class IssueServiceTokenUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        client_id: str,
        client_secret: str,
        requested_scope: str,
        ip: str | None,
        user_agent: str | None,
    ) -> ServiceTokenResult:
        try:
            parsed_id = uuid.UUID(client_id)
        except ValueError:
            raise ServiceClientNotFoundError("credenciales de servicio inválidas") from None
        client = await self._ctx.clients.get_by_id(parsed_id)
        if client is None or not self._ctx.token_hasher.verify(
            client_secret, client.client_secret_hash
        ):
            raise ServiceClientNotFoundError("credenciales de servicio inválidas")
        if not client.enabled:
            raise ServiceClientDisabledError("cliente de servicio deshabilitado")

        scope = self._resolve_scope(requested_scope, client.scopes)
        ttl = 300  # 5 minutos
        token = self._ctx.token_provider.issue_service_token(
            client=client, scope=scope, ttl_seconds=ttl
        )
        await audit(
            self._ctx,
            event_type="service.token.issued",
            actor=str(client.client_id),
            subject=str(client.client_id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"scope": scope},
        )
        return ServiceTokenResult(
            access_token=token,
            token_type="Bearer",
            expires_in=ttl,
            scope=scope,
        )

    @staticmethod
    def _resolve_scope(requested: str, allowed: list[str]) -> str:
        allowed_set = set(allowed)
        requested_set = {s for s in requested.split() if s in VALID_SCOPES}
        granted = requested_set & allowed_set
        if not granted:
            raise ServiceClientNotFoundError("scope no permitido")
        return " ".join(sorted(granted))
