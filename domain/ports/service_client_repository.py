"""Repositorio de clientes de servicio de osap-auth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from domain.entities.service_client import ServiceClient


class ServiceClientRepository(ABC):
    """Persistencia de clientes machine-to-machine."""

    @abstractmethod
    async def get_by_id(self, client_id: uuid.UUID) -> ServiceClient | None: ...

    @abstractmethod
    async def save(self, client: ServiceClient) -> None: ...
