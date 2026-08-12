"""Utilidades de dominio de osap-auth."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    """Interpreta un datetime naive como UTC (MySQL no guarda la zona horaria)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def pkce_challenge(verifier: str, method: str = "S256") -> str:
    """Calcula el code_challenge PKCE (S256) de un code_verifier."""
    if method != "S256":
        raise ValueError("solo se soporta PKCE S256")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
