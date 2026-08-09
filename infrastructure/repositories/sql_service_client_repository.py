"""Repositorio SQL de clientes de servicio de osap-auth."""

from __future__ import annotations

import json
import uuid
from typing import Any

import aiomysql

from domain.entities.service_client import ServiceClient
from domain.ports.service_client_repository import ServiceClientRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> ServiceClient:
    scopes = json.loads(row["scopes"]) if isinstance(row["scopes"], str) else row["scopes"]
    return ServiceClient(
        client_id=uuid.UUID(row["client_id"]),
        client_secret_hash=row["client_secret_hash"],
        scopes=scopes,
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
    )


class SqlServiceClientRepository(ServiceClientRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, client_id: uuid.UUID) -> ServiceClient | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM service_clients WHERE client_id=%s", (str(client_id),))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def save(self, client: ServiceClient) -> None:
        scopes = json.dumps(client.scopes)
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO service_clients
                  (client_id, client_secret_hash, scopes, enabled, created_at)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  client_secret_hash=VALUES(client_secret_hash),
                  scopes=VALUES(scopes),
                  enabled=VALUES(enabled)
                """,
                (
                    str(client.client_id),
                    client.client_secret_hash,
                    scopes,
                    client.enabled,
                    client.created_at,
                ),
            )
