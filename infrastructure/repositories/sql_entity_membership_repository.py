"""Repositorio SQL de pertenencias usuario↔entidad."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import aiomysql

from domain.entities.entity_membership import EntityMembership, MembershipStatus
from domain.ports.entity_membership_repository import EntityMembershipRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> EntityMembership:
    decided_by = row.get("decided_by")
    return EntityMembership(
        id=uuid.UUID(row["id"]),
        entity_id=uuid.UUID(row["entity_id"]),
        user_id=uuid.UUID(row["user_id"]),
        status=MembershipStatus(row["status"]),
        requested_at=row["requested_at"],
        decided_at=row.get("decided_at"),
        decided_by=uuid.UUID(decided_by) if decided_by else None,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


class SqlEntityMembershipRepository(EntityMembershipRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, membership_id: uuid.UUID) -> EntityMembership | None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM entity_memberships WHERE id=%s", (str(membership_id),)
            )
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def get(
        self, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> EntityMembership | None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM entity_memberships WHERE entity_id=%s AND user_id=%s",
                (str(entity_id), str(user_id)),
            )
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[EntityMembership]:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM entity_memberships WHERE user_id=%s ORDER BY requested_at DESC",
                (str(user_id),),
            )
            rows = await cur.fetchall()
        return [_from_row(r) for r in rows]

    async def list_for_entity(self, entity_id: uuid.UUID) -> list[EntityMembership]:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM entity_memberships WHERE entity_id=%s ORDER BY requested_at DESC",
                (str(entity_id),),
            )
            rows = await cur.fetchall()
        return [_from_row(r) for r in rows]

    async def list_pending_for_manager(
        self, manager_id: uuid.UUID
    ) -> list[EntityMembership]:
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                SELECT m.* FROM entity_memberships m
                JOIN entities e ON e.id = m.entity_id
                WHERE e.created_by=%s AND m.status=%s
                ORDER BY m.requested_at
                """,
                (str(manager_id), MembershipStatus.PENDING.value),
            )
            rows = await cur.fetchall()
        return [_from_row(r) for r in rows]

    async def save(self, membership: EntityMembership) -> None:
        now = datetime.now(UTC)
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO entity_memberships
                  (id, entity_id, user_id, status, requested_at, decided_at, decided_by,
                   created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  status=VALUES(status),
                  requested_at=VALUES(requested_at),
                  decided_at=VALUES(decided_at),
                  decided_by=VALUES(decided_by),
                  updated_at=VALUES(updated_at)
                """,
                (
                    str(membership.id),
                    str(membership.entity_id),
                    str(membership.user_id),
                    membership.status.value,
                    membership.requested_at,
                    membership.decided_at,
                    str(membership.decided_by) if membership.decided_by else None,
                    membership.created_at or now,
                    membership.updated_at or now,
                ),
            )

    async def delete(self, membership_id: uuid.UUID) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "DELETE FROM entity_memberships WHERE id=%s", (str(membership_id),)
            )
