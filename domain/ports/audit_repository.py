"""Repositorio de auditoría append-only de osap-auth."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.audit_event import AuditEvent


class AuditRepository(ABC):
    """Persistencia append-only de eventos de seguridad."""

    @abstractmethod
    async def append(self, event: AuditEvent) -> None: ...

    @abstractmethod
    async def last_hash(self) -> str: ...

    @abstractmethod
    async def purge_older_than_days(self, days: int) -> int: ...
