"""Repositorio de usuarios de osap-auth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from domain.entities.user import User


class UserRepository(ABC):
    """Persistencia de usuarios. Solo consultas por id o por email_lookup."""

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email_lookup(self, email_lookup: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def exists(self, email_lookup: str) -> bool: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...
