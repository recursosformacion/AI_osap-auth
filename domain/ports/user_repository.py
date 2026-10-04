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
    async def get_by_ids(self, user_ids: list[uuid.UUID]) -> list[User]:
        """Lookup en lote: devuelve solo las personas que existen (sin orden garantizado)."""

    @abstractmethod
    async def get_by_email_lookup(self, email_lookup: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def exists(self, email_lookup: str) -> bool: ...

    @abstractmethod
    async def nickname_norm_exists(
        self, nickname_norm: str, *, exclude_user_id: uuid.UUID | None = None
    ) -> bool:
        """¿Está tomado ese `nickname_norm` por OTRO usuario? (excluye el propio)."""

    @abstractmethod
    async def list_all(self) -> list[User]: ...

    @abstractmethod
    async def list_public(self) -> list[User]:
        """Usuarios publicables: consentimiento de cuenta activo y `nickname`, no eliminados.

        Es la fuente de la lista pública de colaboradores (la visibilidad es de cuenta, no de
        fila). Orden estable por `nickname` para que la fachada no tenga que reordenar.
        """
