"""Repositorio de entidades agregadoras de usuarios."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from domain.entities.entity import Entity


class EntityRepository(ABC):
    """Persistencia de entidades."""

    @abstractmethod
    async def get_by_id(self, entity_id: uuid.UUID) -> Entity | None: ...

    @abstractmethod
    async def get_by_name_norm(self, name_norm: str) -> Entity | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Entity | None: ...

    @abstractmethod
    async def list_all(self) -> list[Entity]:
        """Listado estable por nombre para el selector de alta/perfil."""

    @abstractmethod
    async def save(self, entity: Entity) -> None: ...
