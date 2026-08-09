"""Rate limiter de osap-auth."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RateLimiter(ABC):
    """Limita peticiones por clave (p.ej. IP) en una ventana deslizante."""

    @abstractmethod
    async def check_and_increment(self, key: str, limit: int, window_seconds: int) -> bool:
        """Devuelve True si se permite la petición, False si excede el límite."""
