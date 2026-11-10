"""Entidad agregadora de usuarios (coral, orquesta, grupo…).

Una entidad es el nombre que un usuario representante ofrece a futuros usuarios para
agruparse (reparto de partituras, incidencias y otras relaciones). Cada usuario puede
pertenecer como máximo a una entidad (`users.entity_id`).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class EntityKind(StrEnum):
    CORAL = "coral"
    ORQUESTA = "orquesta"
    GRUPO = "grupo"


@dataclass
class Entity:
    """Entidad a la que se pueden agrupar usuarios."""

    id: uuid.UUID
    name: str
    name_norm: str
    kind: EntityKind
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    @classmethod
    def new(
        cls,
        *,
        name: str,
        name_norm: str,
        kind: EntityKind,
        created_by: uuid.UUID | None,
    ) -> Entity:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            name=name,
            name_norm=name_norm,
            kind=kind,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
