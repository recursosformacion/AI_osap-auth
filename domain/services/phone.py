"""Teléfono voluntario del usuario para comunicaciones por WhatsApp.

No es un identificador de cuenta (no hay unicidad ni verificación): solo un dato de
contacto opcional que el usuario puede añadir, cambiar o borrar. Se guarda en formato
compacto (dígitos y un `+` inicial opcional).
"""

from __future__ import annotations

import re

from domain.exceptions import InvalidPhoneError

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
_SEPARATORS_RE = re.compile(r"[\s().\-/]")


def normalize(phone: str) -> str:
    """Valida y devuelve el teléfono en formato compacto. 422 si no es válido."""
    cleaned = _SEPARATORS_RE.sub("", phone.strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if _PHONE_RE.fullmatch(cleaned) is None:
        raise InvalidPhoneError("teléfono inválido")
    return cleaned
