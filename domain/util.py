"""Utilidades de dominio de osap-auth."""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    """Interpreta un datetime naive como UTC (MySQL no guarda la zona horaria)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
