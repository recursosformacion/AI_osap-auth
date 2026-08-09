"""Reloj (inyectable para tests)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class Clock(ABC):
    @abstractmethod
    def utcnow(self) -> datetime: ...


class SystemClock(Clock):
    def utcnow(self) -> datetime:
        return datetime.now(UTC)
