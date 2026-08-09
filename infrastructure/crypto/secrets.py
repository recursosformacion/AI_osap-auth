"""Generador de secretos opacos de alta entropía (osap-auth)."""

from __future__ import annotations

import secrets

from domain.ports.crypto import SecretGenerator as SecretGeneratorPort


class SecretGenerator(SecretGeneratorPort):
    def generate(self, byte_length: int) -> str:
        return secrets.token_urlsafe(byte_length)
