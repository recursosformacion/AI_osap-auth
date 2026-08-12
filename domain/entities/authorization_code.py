"""Código de autorización OIDC (Authorization Code) de osap-auth.

Opaco, de un solo uso y de TTL corto. Solo se persiste su hash.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from domain.util import ensure_utc


class AuthorizationCode:
    def __init__(
        self,
        *,
        id: uuid.UUID,
        client_id: str,
        user_id: uuid.UUID,
        redirect_uri: str,
        scope: str,
        code_hash: str,
        expires_at: datetime,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        nonce: str | None = None,
        used_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.client_id = client_id
        self.user_id = user_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.code_hash = code_hash
        self.expires_at = expires_at
        self.code_challenge = code_challenge
        self.code_challenge_method = code_challenge_method
        self.nonce = nonce
        self.used_at = used_at
        self.created_at = created_at

    @property
    def is_expired(self) -> bool:
        return ensure_utc(self.expires_at) <= datetime.now(UTC)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def mark_used(self) -> None:
        self.used_at = datetime.now(UTC)

    @classmethod
    def new(
        cls,
        *,
        client_id: str,
        user_id: uuid.UUID,
        redirect_uri: str,
        scope: str,
        code_hash: str,
        ttl_seconds: int,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        nonce: str | None = None,
    ) -> AuthorizationCode:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_hash=code_hash,
            expires_at=now + timedelta(seconds=ttl_seconds),
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
            created_at=now,
        )
