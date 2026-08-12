"""Repositorio de códigos de autorización OIDC de osap-auth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from domain.entities.authorization_code import AuthorizationCode


class AuthorizationCodeRepository(ABC):
    """Persistencia de códigos de autorización opacos de un solo uso."""

    @abstractmethod
    async def get_by_hash(self, code_hash: str) -> AuthorizationCode | None: ...

    @abstractmethod
    async def save(self, code: AuthorizationCode) -> None: ...

    @abstractmethod
    async def mark_used(self, code_id: uuid.UUID) -> None: ...
