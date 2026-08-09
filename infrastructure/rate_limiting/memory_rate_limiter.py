"""Rate limiter en memoria con ventana deslizante (single-instance).

Para despliegue multi-instancia, sustituir por una implementación distribuida
(Redis) que mantenga el mismo contrato `RateLimiter`.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from domain.ports.rate_limiter import RateLimiter


class MemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def check_and_increment(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        window = self._hits[key]
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True
