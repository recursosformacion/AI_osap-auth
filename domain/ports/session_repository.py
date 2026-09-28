"""Repositorio de sesiones de osap-auth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.session import Session


class SessionRepository(ABC):
    """Persistencia de sesiones revocables."""

    @abstractmethod
    async def get_by_id(self, session_id: uuid.UUID) -> Session | None: ...

    @abstractmethod
    async def get_by_refresh_hash(self, refresh_token_hash: str) -> Session | None: ...

    @abstractmethod
    async def get_by_previous_refresh_hash(
        self, previous_refresh_token_hash: str
    ) -> Session | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID) -> list[Session]: ...

    @abstractmethod
    async def save(self, session: Session) -> None: ...

    @abstractmethod
    async def consume_and_rotate(
        self,
        session_id: uuid.UUID,
        expected_refresh_hash: str,
        new_refresh_hash: str,
        new_expires_at: datetime,
    ) -> bool:
        """Rota el refresh de forma atómica (compare-and-swap).

        Devuelve `True` solo si esta llamada consumió el token: la fila sigue teniendo
        `expected_refresh_hash`, no está revocada y no ha expirado. Bajo doble consumo
        concurrente, exactamente una llamada obtiene `True`.
        """
        ...

    @abstractmethod
    async def revoke(self, session_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None: ...
