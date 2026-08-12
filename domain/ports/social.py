"""Ports del login social (upstream): proveedores OAuth2/OIDC externos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderProfile:
    sub: str
    email: str | None
    name: str | None
    email_verified: bool


class SocialProvider(ABC):
    """Cliente de un proveedor social externo (authorization code + PKCE)."""

    name: str

    @abstractmethod
    def authorize_url(self, redirect_uri: str, state: str, code_challenge: str) -> str: ...

    @abstractmethod
    async def exchange_and_profile(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> ProviderProfile: ...
