"""Repositorio SQL de sesiones de osap-auth."""

from __future__ import annotations

import uuid
from typing import Any

import aiomysql

from domain.entities.session import Session
from domain.ports.session_repository import SessionRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> Session:
    return Session(
        id=uuid.UUID(row["id"]),
        user_id=uuid.UUID(row["user_id"]),
        refresh_token_hash=row["refresh_token_hash"],
        previous_refresh_token_hash=row["previous_refresh_token_hash"],
        refresh_expires_at=row["refresh_expires_at"],
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
        revoked_at=row["revoked_at"],
        client_id=row["client_id"] if row.get("client_id") else None,
        ip=row["ip"],
        user_agent=row["user_agent"],
        device_label=row["device_label"],
    )


class SqlSessionRepository(SessionRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM sessions WHERE id=%s", (str(session_id),))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def get_by_refresh_hash(self, refresh_token_hash: str) -> Session | None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM sessions WHERE refresh_token_hash=%s", (refresh_token_hash,)
            )
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def get_by_previous_refresh_hash(
        self, previous_refresh_token_hash: str
    ) -> Session | None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM sessions WHERE previous_refresh_token_hash=%s",
                (previous_refresh_token_hash,),
            )
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[Session]:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM sessions WHERE user_id=%s ORDER BY created_at DESC",
                (str(user_id),),
            )
            rows = await cur.fetchall()
        return [_from_row(r) for r in rows]

    async def save(self, session: Session) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO sessions
                  (id, user_id, refresh_token_hash, previous_refresh_token_hash,
                   refresh_expires_at, created_at, last_used_at, revoked_at,
                   client_id, ip, user_agent, device_label)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  refresh_token_hash=VALUES(refresh_token_hash),
                  previous_refresh_token_hash=VALUES(previous_refresh_token_hash),
                  refresh_expires_at=VALUES(refresh_expires_at),
                  last_used_at=VALUES(last_used_at),
                  revoked_at=VALUES(revoked_at)
                """,
                (
                    str(session.id),
                    str(session.user_id),
                    session.refresh_token_hash,
                    session.previous_refresh_token_hash,
                    session.refresh_expires_at,
                    session.created_at,
                    session.last_used_at,
                    session.revoked_at,
                    str(session.client_id) if session.client_id else None,
                    session.ip,                    session.user_agent,
                    session.device_label,
                ),
            )

    async def revoke(self, session_id: uuid.UUID) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "UPDATE sessions SET revoked_at=NOW(6) WHERE id=%s AND revoked_at IS NULL",
                (str(session_id),),
            )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "UPDATE sessions SET revoked_at=NOW(6) WHERE user_id=%s AND revoked_at IS NULL",
                (str(user_id),),
            )
