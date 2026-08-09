"""Ports de criptografía y tokens de osap-auth."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Hash de contraseñas (Argon2id)."""

    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool: ...

    def dummy_verify(self) -> None:
        """Ejecuta una verificación ficticia para igualar tiempos (anti-enumeración)."""
        self.hash("dummy-constant-password")


class TokenHasher(ABC):
    """Hash de tokens opacos (refresh, verificación, reset)."""

    @abstractmethod
    def hash(self, token: str) -> str: ...

    @abstractmethod
    def verify(self, token: str, hashed: str) -> bool: ...


class SecretGenerator(ABC):
    """Genera secretos opacos de alta entropía."""

    @abstractmethod
    def generate(self, byte_length: int) -> str: ...


class EmailProtector(ABC):
    """Protege el email: HMAC para localizar (lookup) y AEAD para mostrar (cipher)."""

    @abstractmethod
    def lookup(self, email: str) -> str: ...

    @abstractmethod
    def encrypt(self, email: str) -> bytes: ...

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> str: ...
