"""Hashes Argon2id para contraseñas y tokens opacos de osap-auth."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from domain.ports.crypto import PasswordHasher as PasswordHasherPort
from domain.ports.crypto import TokenHasher

# Parámetros orientados a seguridad: suficiente coste sin latencia excesiva.
_TIME_COST = 3
_MEMORY_KIB = 64 * 1024
_PARALLELISM = 2


class Argon2PasswordHasher(PasswordHasherPort):
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=_TIME_COST,
            memory_cost=_MEMORY_KIB,
            parallelism=_PARALLELISM,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False

    def dummy_verify(self) -> None:
        try:
            self._hasher.verify(self.hash("dummy-constant-password"), "does-not-match")
        except VerifyMismatchError:
            pass


class Argon2TokenHasher(TokenHasher):
    """Hash de tokens opacos. Usa Argon2id pero con coste reducido (los tokens ya
    son alta entropía, el coste protege el hash ante una fuga de la BD)."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=2,
            memory_cost=32 * 1024,
            parallelism=1,
        )

    def hash(self, token: str) -> str:
        return self._hasher.hash(token)

    def verify(self, token: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, token)
        except VerifyMismatchError:
            return False
