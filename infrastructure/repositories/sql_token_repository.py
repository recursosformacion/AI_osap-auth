"""Repositorio SQL de tokens de un solo uso de osap-auth."""

from __future__ import annotations

import uuid
from typing import Any

import aiomysql

from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.ports.token_repository import TokenRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> TokenRecord:
    return TokenRecord(
        id=uuid.UUID(row["id"]),
        user_id=uuid.UUID(row["user_id"]),
        purpose=TokenPurpose(row["purpose"]),
        token_hash=row["token_hash"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
        created_at=row["created_at"],
    )


class SqlTokenRepository(TokenRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_hash(self, token_hash: str, purpose: TokenPurpose) -> TokenRecord | None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM tokens WHERE token_hash=%s AND purpose=%s",
                (token_hash, purpose.value),
            )
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def save(self, token: TokenRecord) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO tokens
                  (id, user_id, purpose, token_hash, expires_at, used_at, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(token.id),
                    str(token.user_id),
                    token.purpose.value,
                    token.token_hash,
                    token.expires_at,
                    token.used_at,
                    token.created_at,
                ),
            )

    async def mark_used(self, token_id: uuid.UUID) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "UPDATE tokens SET used_at=NOW(6) WHERE id=%s AND used_at IS NULL",
                (str(token_id),),
            )
