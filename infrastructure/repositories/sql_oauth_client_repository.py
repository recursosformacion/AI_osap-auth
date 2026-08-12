"""Repositorio SQL de clientes OAuth2/OIDC (relying parties) de osap-auth."""

from __future__ import annotations

import json
from typing import Any

import aiomysql

from domain.entities.oauth_client import OAuthClient
from domain.ports.oauth_client_repository import OAuthClientRepository
from infrastructure.repositories._helpers import cursor


def _json(row_value: Any, key: str) -> list[str]:
    value = row_value.get(key) if isinstance(row_value, dict) else row_value
    if isinstance(value, str):
        return json.loads(value)
    return value or []


def _from_row(row: dict[str, Any]) -> OAuthClient:
    return OAuthClient(
        client_id=row["client_id"],
        client_secret_hash=row["client_secret_hash"],
        redirect_uris=_json(row, "redirect_uris"),
        allowed_redirect_hosts=_json(row, "allowed_redirect_hosts"),
        grant_types=_json(row, "grant_types"),
        response_types=_json(row, "response_types"),
        allowed_scopes=_json(row, "allowed_scopes"),
        pkce_required=bool(row["pkce_required"]),
        token_endpoint_auth_method=row["token_endpoint_auth_method"],
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
    )


class SqlOAuthClientRepository(OAuthClientRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, client_id: str) -> OAuthClient | None:
        async with cursor(self._pool) as cur:
            await cur.execute("SELECT * FROM oauth_clients WHERE client_id=%s", (client_id,))
            row = await cur.fetchone()
        return _from_row(row) if row else None

    async def save(self, client: OAuthClient) -> None:
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO oauth_clients
                  (client_id, client_secret_hash, redirect_uris, allowed_redirect_hosts,
                   grant_types, response_types, allowed_scopes, pkce_required,
                   token_endpoint_auth_method, enabled, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  client_secret_hash=VALUES(client_secret_hash),
                  redirect_uris=VALUES(redirect_uris),
                  allowed_redirect_hosts=VALUES(allowed_redirect_hosts),
                  grant_types=VALUES(grant_types),
                  response_types=VALUES(response_types),
                  allowed_scopes=VALUES(allowed_scopes),
                  pkce_required=VALUES(pkce_required),
                  token_endpoint_auth_method=VALUES(token_endpoint_auth_method),
                  enabled=VALUES(enabled)
                """,
                (
                    client.client_id,
                    client.client_secret_hash,
                    json.dumps(client.redirect_uris),
                    json.dumps(client.allowed_redirect_hosts),
                    json.dumps(client.grant_types),
                    json.dumps(client.response_types),
                    json.dumps(client.allowed_scopes),
                    client.pkce_required,
                    client.token_endpoint_auth_method,
                    client.enabled,
                    client.created_at,
                ),
            )
