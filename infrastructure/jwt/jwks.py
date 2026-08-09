"""Utilidades de clave JWK (RFC 7517) para osap-auth."""

from __future__ import annotations

import base64
from typing import Any


def b64u_int(value: int) -> str:
    """Codifica un entero sin signo como base64url (sin relleno)."""
    length = (value.bit_length() + 7) // 8
    raw = value.to_bytes(length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def jwk_from_public_key(pub: Any, kid: str) -> dict[str, str]:
    """Convierte una clave pública RSA a un JWK (RFC 7517)."""
    numbers = pub.public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": b64u_int(numbers.n),
        "e": b64u_int(numbers.e),
    }
