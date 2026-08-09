"""Publicador de eventos de dominio de osap-auth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod


class EventPublisher(ABC):
    """Publica eventos de dominio para otros servicios (p.ej. `user.deleted`)."""

    @abstractmethod
    async def publish_user_deleted(self, user_id: uuid.UUID, deleted_at: str) -> None: ...
