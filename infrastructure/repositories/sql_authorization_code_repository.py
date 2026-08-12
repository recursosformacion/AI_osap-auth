"""Repositorio SQL de códigos de autorización OIDC de osap-auth."""

from __future__ import annotations

import uuid
from typing import Any

import aiomysql

from domain.entities.authorization_code import AuthorizationCode
from domain.ports.authorization_code_repository import AuthorizationCodeRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> AuthorizationCode:
    return AuthorizationCode(
        id=uuid.UUID(row["id"]),
        client_id=row["client_id"],
        user_id=uuid.UUID(row["user_id"]),
        redirect_uri=row["redirect_uri"],
        scope=row["scope"],
        code_hash=row["code_hash"],
        expires_at=row["expires_at"],
        code_challenge=row["code_challenge"],
        code_challenge_method=row["code_challenge_method"],
        nonce=row["nonce"],
        used_at=row["used_at"],
        created_at=row["created_at"],
    )


class SqlAuthorizationCodeRepository(AuthorizationCodeRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_hash(self, code_hash: str) -> AuthorizationCode | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM authorization_codes WHERE code_hash=%s", (code_hash,))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def save(self, code: AuthorizationCode) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO authorization_codes
                  (id, client_id, user_id, redirect_uri, scope, code_hash,
                   expires_at, code_challenge, code_challenge_method, nonce,
                   used_at, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(code.id),
                    code.client_id,
                    str(code.user_id),
                    code.redirect_uri,
                    code.scope,
                    code.code_hash,
                    code.expires_at,
                    code.code_challenge,
                    code.code_challenge_method,
                    code.nonce,
                    code.used_at,
                    code.created_at,
                ),
            )

    async def mark_used(self, code_id: uuid.UUID) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "UPDATE authorization_codes SET used_at=NOW(6) WHERE id=%s AND used_at IS NULL",
                (str(code_id),),
            )
