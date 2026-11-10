"""Pertenencia de un usuario a una entidad (con aprobación del gestor).

Un usuario puede solicitar pertenecer a varias entidades. La solicitud queda `pending`
hasta que el gestor de la entidad (su `created_by`) la aprueba o rechaza. Solo las
`approved` cuentan como pertenencia efectiva. El representante que crea una entidad
queda como miembro `approved` automáticamente.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class MembershipStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class EntityMembership:
    id: uuid.UUID
    entity_id: uuid.UUID
    user_id: uuid.UUID
    status: MembershipStatus
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def approve(self, decided_by: uuid.UUID) -> None:
        self.status = MembershipStatus.APPROVED
        self.decided_at = datetime.now(UTC)
        self.decided_by = decided_by
        self.touch()

    def reject(self, decided_by: uuid.UUID) -> None:
        self.status = MembershipStatus.REJECTED
        self.decided_at = datetime.now(UTC)
        self.decided_by = decided_by
        self.touch()

    def re_request(self) -> None:
        """Reabre una solicitud rechazada sin cambiar la fila (misma entidad/usuario)."""
        self.status = MembershipStatus.PENDING
        self.requested_at = datetime.now(UTC)
        self.decided_at = None
        self.decided_by = None
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    @classmethod
    def new(
        cls,
        *,
        entity_id: uuid.UUID,
        user_id: uuid.UUID,
        status: MembershipStatus,
        decided_by: uuid.UUID | None = None,
    ) -> EntityMembership:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            entity_id=entity_id,
            user_id=user_id,
            status=status,
            requested_at=now,
            decided_at=now if status is MembershipStatus.APPROVED else None,
            decided_by=decided_by,
            created_at=now,
            updated_at=now,
        )
