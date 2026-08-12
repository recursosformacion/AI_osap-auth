"""Repositorio de cuentas vinculadas a proveedores sociales (upstream)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.provider_account import ProviderAccount


class ProviderAccountRepository(ABC):
    """Persistencia del vínculo provider_sub <-> user_id."""

    @abstractmethod
    async def get_by_provider_sub(
        self, provider: str, provider_sub: str
    ) -> ProviderAccount | None: ...

    @abstractmethod
    async def save(self, account: ProviderAccount) -> None: ...
