"""Reglas del `nickname` (handle único): normalización, formato y reservados.

`nickname` es un handle corto **distinto** de `name` (nombre visible). Se normaliza con
`trim` + NFKC + casefold para unicidad case-insensitive; el formato es ASCII:
`^[a-z][a-z0-9_-]{1,28}[a-z0-9]$` (3–30, empieza por letra, termina en letra/número).
"""

from __future__ import annotations

import re
import unicodedata

from domain.exceptions import InvalidNicknameError

_NICKNAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,28}[a-z0-9]$")

# Reservados: no asignables a usuarios (evita colisiones con rutas/roles/servicios).
RESERVED: frozenset[str] = frozenset(
    {
        "admin", "administrator", "root", "system", "support", "help", "api", "auth",
        "www", "web", "app", "osap", "openmusicrepository", "login", "logout", "register",
        "onboarding", "settings", "profile", "me", "user", "users", "account", "billing",
        "legal", "terms", "privacy", "collaborators", "composer", "composers", "works",
    }
)


def normalize(nickname: str) -> str:
    """Forma canónica para comparar/almacenar: `trim` + NFKC + casefold."""
    return unicodedata.normalize("NFKC", nickname.strip()).casefold()


def validate(nickname: str) -> str:
    """Valida y devuelve la forma normalizada. Lanza `InvalidNicknameError` (422) si no vale."""
    norm = normalize(nickname)
    if _NICKNAME_RE.fullmatch(norm) is None:
        raise InvalidNicknameError("nickname inválido")
    if norm in RESERVED:
        raise InvalidNicknameError("nickname reservado")
    return norm
