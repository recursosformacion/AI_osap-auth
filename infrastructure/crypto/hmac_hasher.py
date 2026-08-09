"""Hash determinista (HMAC-SHA256) para tokens opacos de alta entropía.

Los tokens de un solo uso y los refresh tokens son aleatorios de alta entropía. Para
poder localizarlos por valor (single-use / rotación / detección de reuso) se usa un
digest determinista y no reversible. Argon2id queda reservado para contraseñas
(secretos de baja entropía), donde no se necesita búsqueda indexada.
"""

from __future__ import annotations

import hashlib
import hmac

from domain.ports.crypto import TokenHasher


class HmacTokenHasher(TokenHasher):
    def __init__(self, pepper: str) -> None:
        self._pepper = pepper.encode("utf-8")

    def hash(self, token: str) -> str:
        return hmac.new(self._pepper, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, token: str, hashed: str) -> bool:
        return hmac.compare_digest(self.hash(token), hashed)
