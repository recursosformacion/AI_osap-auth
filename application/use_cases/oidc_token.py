"""Casos de uso OIDC del token endpoint: canje de code y refresh con rotación."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from application.audit import audit
from application.context import AuthContext
from domain.entities.oauth_client import OAuthClient
from domain.entities.session import Session
from domain.exceptions import (
    InvalidTokenError,
    OAuthClientNotFoundError,
    OAuthError,
    TokenReuseDetectedError,
)
from domain.util import ensure_utc, pkce_challenge


@dataclass
class TokenResult:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str


async def _authenticate_client(
    ctx: AuthContext, client_id: str, client_secret: str
) -> OAuthClient:
    if not client_id:
        raise OAuthClientNotFoundError("invalid_client")
    client = await ctx.oauth_clients.get_by_id(client_id)
    if client is None or not client.enabled:
        raise OAuthClientNotFoundError("invalid_client")
    if not client.client_secret_hash or not ctx.token_hasher.verify(
        client_secret, client.client_secret_hash
    ):
        raise OAuthClientNotFoundError("invalid_client")
    return client


class ExchangeAuthorizationCodeUseCase:
    """Canjea un Authorization Code por access + refresh token (PKCE S256)."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResult:
        client = await _authenticate_client(self._ctx, client_id, client_secret)
        if not client.allows_grant("authorization_code"):
            raise OAuthError("unauthorized_client", "grant no permitido")

        record = await self._ctx.authorization_codes.get_by_hash(
            self._ctx.token_hasher.hash(code)
        )
        if record is None or record.is_used or record.is_expired:
            raise OAuthError("invalid_grant", "code inválido, usado o caducado")
        if record.client_id != client.client_id:
            raise OAuthError("invalid_grant", "code no pertenece a este cliente")
        if record.redirect_uri != redirect_uri:
            raise OAuthError("invalid_grant", "redirect_uri no coincide")

        if record.code_challenge:
            challenge = pkce_challenge(code_verifier, record.code_challenge_method or "S256")
            if not code_verifier or not _constant_eq(challenge, record.code_challenge):
                raise OAuthError("invalid_grant", "code_verifier no válido (PKCE)")
        elif client.pkce_required:
            raise OAuthError("invalid_request", "PKCE requerido")

        await self._ctx.authorization_codes.mark_used(record.id)

        raw_refresh = self._ctx.secret_generator.generate(48)
        session = Session.new(
            user_id=record.user_id,
            refresh_token_hash=self._ctx.token_hasher.hash(raw_refresh),
            refresh_ttl_seconds=self._ctx.settings.refresh_token_ttl_seconds,
            client_id=client.client_id,
            ip=ip,
            user_agent=user_agent,
        )
        await self._ctx.sessions.save(session)

        access = await self._issue_access(
            client, record.user_id, session, record.scope, record.nonce
        )
        await audit(
            self._ctx,
            event_type="oauth.token",
            actor=str(record.user_id),
            subject=str(record.user_id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"client": str(client.client_id), "grant": "authorization_code"},
        )
        return TokenResult(
            access_token=access,
            refresh_token=raw_refresh,
            token_type="Bearer",
            expires_in=self._ctx.settings.access_token_ttl_seconds,
            scope=record.scope,
        )

    async def _issue_access(
        self,
        client: OAuthClient,
        user_id: uuid.UUID,
        session: Session,
        scope: str,
        nonce: str | None,
    ) -> str:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            raise OAuthError("invalid_grant", "usuario no encontrado")
        return self._ctx.token_provider.issue_access_token(
            user_id=user_id,
            session_id=session.id,
            roles=user.roles,
            email_verified=user.email_verified,
            scope=scope,
            ttl_seconds=self._ctx.settings.access_token_ttl_seconds,
            audience=str(client.client_id),
            nonce=nonce,
            issuer=self._ctx.settings.effective_issuer,
        )


class RefreshTokenGrantUseCase:
    """Renueva access token vía refresh_token con rotación y detección de reuso."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResult:
        client = await _authenticate_client(self._ctx, client_id, client_secret)
        if not client.allows_grant("refresh_token"):
            raise OAuthError("unauthorized_client", "grant no permitido")

        provided_hash = self._ctx.token_hasher.hash(refresh_token)
        session = await self._ctx.sessions.get_by_refresh_hash(provided_hash)

        if session is None:
            reused = await self._ctx.sessions.get_by_previous_refresh_hash(provided_hash)
            if reused is not None:
                await self._ctx.sessions.revoke_all_for_user(reused.user_id)
                raise TokenReuseDetectedError("refresh reutilizado; sesiones revocadas")
            raise InvalidTokenError("refresh token inválido")

        if session.client_id != client.client_id:
            raise OAuthError("invalid_grant", "refresh no pertenece a este cliente")
        if (
            session.revoked_at is not None
            or ensure_utc(session.refresh_expires_at) <= datetime.now(UTC)
        ):
            raise InvalidTokenError("refresh token inválido")

        new_refresh = self._ctx.secret_generator.generate(48)
        session.previous_refresh_token_hash = session.refresh_token_hash
        session.refresh_token_hash = self._ctx.token_hasher.hash(new_refresh)
        session.touch()
        session.refresh_expires_at = datetime.now(UTC) + timedelta(
            seconds=self._ctx.settings.refresh_token_ttl_seconds
        )
        await self._ctx.sessions.save(session)

        user = await self._ctx.users.get_by_id(session.user_id)
        if user is None:
            raise InvalidTokenError("refresh token inválido")

        access = self._ctx.token_provider.issue_access_token(
            user_id=user.id,
            session_id=session.id,
            roles=user.roles,
            email_verified=user.email_verified,
            scope="openid profile",
            ttl_seconds=self._ctx.settings.access_token_ttl_seconds,
            audience=str(client.client_id),
            issuer=self._ctx.settings.effective_issuer,
        )
        await audit(
            self._ctx,
            event_type="oauth.token",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"client": str(client.client_id), "grant": "refresh_token"},
        )
        return TokenResult(
            access_token=access,
            refresh_token=new_refresh,
            token_type="Bearer",
            expires_in=self._ctx.settings.access_token_ttl_seconds,
            scope="openid profile",
        )


def _constant_eq(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left.encode(), right.encode())
