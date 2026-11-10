"""Repositorio de pertenencias usuario↔entidad."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from domain.entities.entity_membership import EntityMembership


class EntityMembershipRepository(ABC):
    """Persistencia de solicitudes y pertenencias aprobadas."""

    @abstractmethod
    async def get_by_id(self, membership_id: uuid.UUID) -> EntityMembership | None: ...

    @abstractmethod
    async def get(
        self, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> EntityMembership | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID) -> list[EntityMembership]: ...

    @abstractmethod
    async def list_for_entity(self, entity_id: uuid.UUID) -> list[EntityMembership]: ...

    @abstractmethod
    async def list_pending_for_manager(
        self, manager_id: uuid.UUID
    ) -> list[EntityMembership]:
        """Solicitudes pendientes de las entidades que gestiona `manager_id`."""

    @abstractmethod
    async def save(self, membership: EntityMembership) -> None: ...

    @abstractmethod
    async def delete(self, membership_id: uuid.UUID) -> None: ...
