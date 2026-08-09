"""Protección del email de osap-auth.

- `lookup(email)`  → HMAC-SHA256(email_normalizado, pepper): SOLO para localizar la cuenta.
- `encrypt(email)` → AES-256-GCM: SOLO para recuperar y mostrar el email.
- `decrypt(...)`   → invierte `encrypt`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from domain.ports.crypto import EmailProtector
from domain.services.email_utils import normalize_email

_GCM_NONCE_BYTES = 12


def _decode_key(b64: str) -> bytes:
    return base64.urlsafe_b64decode(b64 + "===")


class AesGcmEmailProtector(EmailProtector):
    """Cifra el email con AES-256-GCM. La clave se obtiene de configuración (KEK/DEK)."""

    def __init__(self, *, aead_key_b64: str, pepper: str) -> None:
        self._pepper = pepper.encode("utf-8")
        self._key = _decode_key(aead_key_b64)

    def lookup(self, email: str) -> str:
        normalized = normalize_email(email)
        digest = hmac.new(self._pepper, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    def encrypt(self, email: str) -> bytes:
        normalized = normalize_email(email)
        nonce = secrets.token_bytes(_GCM_NONCE_BYTES)
        ciphertext = AESGCM(self._key).encrypt(nonce, normalized.encode("utf-8"), None)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> str:
        if len(ciphertext) < _GCM_NONCE_BYTES:
            raise ValueError("ciphertext inválido")
        nonce = ciphertext[:_GCM_NONCE_BYTES]
        payload = ciphertext[_GCM_NONCE_BYTES:]
        try:
            plaintext = AESGCM(self._key).decrypt(nonce, payload, None)
        except InvalidTag:
            raise ValueError("email ciphertext inválido") from None
        return plaintext.decode("utf-8")
