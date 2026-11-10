"""Repositorio SQL de entidades agregadoras de usuarios."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import aiomysql
import pymysql

from domain.entities.entity import Entity, EntityKind
from domain.exceptions import EntityTakenError
from domain.ports.entity_repository import EntityRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> Entity:
    created_by = row.get("created_by")
    return Entity(
        id=uuid.UUID(row["id"]),
        name=row["name"],
        name_norm=row["name_norm"],
        kind=EntityKind(row["kind"]),
        created_by=uuid.UUID(created_by) if created_by else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        email=row.get("email"),
    )


class SqlEntityRepository(EntityRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, entity_id: uuid.UUID) -> Entity | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM entities WHERE id=%s", (str(entity_id),))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def get_by_name_norm(self, name_norm: str) -> Entity | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM entities WHERE name_norm=%s", (name_norm,))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def get_by_email(self, email: str) -> Entity | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM entities WHERE email=%s", (email,))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def list_all(self) -> list[Entity]:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM entities ORDER BY name")
            rows = await cur.fetchall()
        return [_from_row(r) for r in rows]

    async def save(self, entity: Entity) -> None:
        now = datetime.now(UTC)
        try:
            async with cursor(self._pool) as cur:
                await cur.execute(
                    """
                    INSERT INTO entities
                      (id, name, name_norm, kind, created_by, created_at, updated_at, email)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      name=VALUES(name),
                      name_norm=VALUES(name_norm),
                      kind=VALUES(kind),
                      email=VALUES(email),
                      updated_at=VALUES(updated_at)
                    """,
                    (
                        str(entity.id),
                        entity.name,
                        entity.name_norm,
                        entity.kind.value,
                        str(entity.created_by) if entity.created_by else None,
                        entity.created_at or now,
                        entity.updated_at or now,
                        entity.email,
                    ),
                )
        except pymysql.err.IntegrityError as exc:
            if "uq_entities_name_norm" in str(exc):
                raise EntityTakenError("nombre de entidad no disponible") from exc
            if "uq_entities_email" in str(exc):
                raise EntityTakenError("correo de entidad no disponible") from exc
            raise
