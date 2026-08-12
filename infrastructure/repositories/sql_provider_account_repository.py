"""Repositorio SQL de cuentas de proveedor social (upstream)."""

from __future__ import annotations

import uuid
from typing import Any

import aiomysql

from domain.entities.provider_account import ProviderAccount
from domain.ports.provider_account_repository import ProviderAccountRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> ProviderAccount:
    return ProviderAccount(
        id=uuid.UUID(row["id"]),
        provider=row["provider"],
        provider_sub=row["provider_sub"],
        user_id=uuid.UUID(row["user_id"]),
        email=row["email"],
        name=row["name"],
        linked_at=row["linked_at"],
    )


class SqlProviderAccountRepository(ProviderAccountRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_provider_sub(self, provider: str, provider_sub: str) -> ProviderAccount | None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT * FROM provider_accounts WHERE provider=%s AND provider_sub=%s",
                (provider, provider_sub),
            )
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def save(self, account: ProviderAccount) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO provider_accounts
                  (id, provider, provider_sub, user_id, email, name, linked_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  email=VALUES(email), name=VALUES(name)
                """,
                (
                    str(account.id),
                    account.provider,
                    account.provider_sub,
                    str(account.user_id),
                    account.email,
                    account.name,
                    account.linked_at,
                ),
            )
