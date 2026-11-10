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
