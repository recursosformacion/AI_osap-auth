"""Repositorio de tokens de un solo uso (verificación / recuperación)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from domain.entities.token_record import TokenPurpose, TokenRecord


class TokenRepository(ABC):
    """Persistencia de tokens opacos de un solo uso (solo su hash)."""

    @abstractmethod
    async def get_by_hash(self, token_hash: str, purpose: TokenPurpose) -> TokenRecord | None: ...

    @abstractmethod
    async def save(self, token: TokenRecord) -> None: ...

    @abstractmethod
    async def consume(self, token_id: uuid.UUID) -> bool:
        """Marca el token como usado de forma atómica (CAS).

        Devuelve `True` solo si esta llamada lo consumió; bajo doble uso concurrente,
        exactamente una llamada obtiene `True`.
        """
        ...
