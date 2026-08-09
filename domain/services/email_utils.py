"""Utilidades de dominio: normalización de email y política de contraseña."""

from __future__ import annotations

import re

from domain.exceptions import InvalidEmailError, WeakPasswordError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def normalize_email(email: str) -> str:
    """Normaliza el email antes de cifrar/hashear (anti-abuso, deduplicación).

    Normaliza la parte local (punto) solo en dominios que lo permiten y reduce
    el dominio a minúsculas. Es determinista y reproducible.
    """
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise InvalidEmailError("email invalido")
    local, _, domain = email.partition("@")
    # Gmail: los puntos en la parte local son ignorables.
    if domain == "gmail.com":
        local = local.replace(".", "")
    return f"{local}@{domain}"


def validate_password(password: str) -> None:
    """Valida la política mínima de contraseña (contra-rociado de credenciales)."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError("password demasiado corta")
