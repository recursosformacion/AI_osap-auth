"""Caso de uso: alta de clientes de servicio (bootstrap/administración)."""

from __future__ import annotations

from dataclasses import dataclass

from application.context import AuthContext
from domain.entities.service_client import VALID_SCOPES, ServiceClient
from domain.exceptions import ServiceClientNotFoundError


@dataclass
class CreateServiceClientResult:
    client_id: str
    client_secret: str


class CreateServiceClientUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        scopes: list[str],
        allowed_audiences: list[str] | None = None,
    ) -> CreateServiceClientResult:
        invalid = [s for s in scopes if s not in VALID_SCOPES]
        if invalid:
            raise ServiceClientNotFoundError(f"scopes inválidos: {invalid}")

        raw_secret = self._ctx.secret_generator.generate(48)
        client = ServiceClient.new(
            client_secret_hash=self._ctx.token_hasher.hash(raw_secret),
            scopes=scopes,
            allowed_audiences=allowed_audiences,
        )
        await self._ctx.clients.save(client)
        return CreateServiceClientResult(client_id=str(client.client_id), client_secret=raw_secret)
