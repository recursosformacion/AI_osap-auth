"""Reglas del nombre y tipo de una entidad (coral, orquesta, grupo).

El nombre visible conserva el formato introducido (trim + espacios colapsados); la
comparación de unicidad usa NFKC + casefold, igual que el nickname.
"""

from __future__ import annotations

import unicodedata

from domain.entities.entity import EntityKind
from domain.exceptions import InvalidEntityError

ENTITY_KINDS: frozenset[str] = frozenset(kind.value for kind in EntityKind)

MAX_NAME_LENGTH = 120
MIN_NAME_LENGTH = 2
MAX_EMAIL_LENGTH = 254


def clean_name(name: str) -> str:
    """Nombre visible normalizado para almacenar: trim, NFKC y espacios colapsados."""
    cleaned = " ".join(unicodedata.normalize("NFKC", name).strip().split())
    if not (MIN_NAME_LENGTH <= len(cleaned) <= MAX_NAME_LENGTH):
        raise InvalidEntityError("nombre de entidad inválido")
    return cleaned


def normalize_name(name: str) -> str:
    """Forma canónica para detectar duplicados (case-insensitive)."""
    return clean_name(name).casefold()


def validate_kind(kind: str) -> EntityKind:
    """Valida el tipo de entidad. Lanza `InvalidEntityError` (422) si no vale."""
    cleaned = kind.strip().casefold()
    if cleaned not in ENTITY_KINDS:
        raise InvalidEntityError("tipo de entidad inválido")
    return EntityKind(cleaned)


def validate_email(email: str) -> str:
    """Correo de contacto de la entidad en minúsculas y con formato comprobado.

    No envía correo ni marca el dominio: la verificación por enlace queda para una
    entrega posterior, cuando se decida si se escribe al grupo.
    """
    cleaned = email.strip().casefold()
    if not cleaned or len(cleaned) > MAX_EMAIL_LENGTH:
        raise InvalidEntityError("correo de entidad inválido")
    local, separator, domain = cleaned.partition("@")
    if (
        not separator
        or not local
        or not domain
        or "." not in domain
        or any(character.isspace() for character in cleaned)
        or domain.startswith(".")
        or domain.endswith(".")
    ):
        raise InvalidEntityError("correo de entidad inválido")
    return cleaned
