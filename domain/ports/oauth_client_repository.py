"""Repositorio de clientes OAuth2/OIDC (relying parties) de osap-auth."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.oauth_client import OAuthClient


class OAuthClientRepository(ABC):
    """Persistencia de clientes RP (Authorization Code + PKCE)."""

    @abstractmethod
    async def get_by_id(self, client_id: str) -> OAuthClient | None: ...

    @abstractmethod
    async def save(self, client: OAuthClient) -> None: ...
