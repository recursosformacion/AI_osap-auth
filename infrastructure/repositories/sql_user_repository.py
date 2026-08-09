"""Repositorio SQL de usuarios de osap-auth."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import aiomysql

from domain.entities.user import User, UserStatus
from domain.ports.user_repository import UserRepository
from infrastructure.repositories._helpers import cursor


def _parse_bool(row: dict[str, Any]) -> bool:
    return bool(row["email_verified_at"])


def _from_row(row: dict[str, Any]) -> User:
    roles = json.loads(row["roles"]) if isinstance(row["roles"], str) else row["roles"]
    verified = row["email_verified_at"]
    return User(
        id=uuid.UUID(row["id"]),
        email_lookup=row["email_lookup"],
        email_cipher=row["email_cipher"],
        password_hash=row["password_hash"],
        status=UserStatus(row["status"]),
        roles=roles,
        key_version=int(row["key_version"]),
        name=row.get("name"),
        email_verified_at=verified,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SqlUserRepository(UserRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM users WHERE id=%s", (str(user_id),))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def get_by_email_lookup(self, email_lookup: str) -> User | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM users WHERE email_lookup=%s", (email_lookup,))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def exists(self, email_lookup: str) -> bool:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT 1 FROM users WHERE email_lookup=%s", (email_lookup,))
            return await cur.fetchone() is not None

    async def list_all(self) -> list[User]:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = await cur.fetchall()
        return [_from_row(r) for r in rows]

    async def save(self, user: User) -> None:
        roles = json.dumps(user.roles)
        now = datetime.now(UTC)
        updated = user.updated_at or now
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO users
                  (id, email_lookup, email_cipher, email_verified_at, password_hash,
                   roles, status, key_version, name, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  email_cipher=VALUES(email_cipher),
                  email_verified_at=VALUES(email_verified_at),
                  password_hash=VALUES(password_hash),
                  roles=VALUES(roles),
                  status=VALUES(status),
                  key_version=VALUES(key_version),
                  name=VALUES(name),
                  updated_at=VALUES(updated_at)
                """,
                (
                    str(user.id),
                    user.email_lookup,
                    user.email_cipher,
                    user.email_verified_at,
                    user.password_hash,
                    roles,
                    user.status.value,
                    user.key_version,
                    user.name,
                    user.created_at or now,
                    updated,
                ),
            )
