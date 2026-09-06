"""Caso de uso: refresh con rotación y detección de reutilización."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from application.audit import audit
from application.context import AuthContext
from domain.exceptions import InvalidTokenError, TokenReuseDetectedError, UnauthorizedError
from domain.util import ensure_utc


@dataclass
class RefreshResult:
    access_token: str
    refresh_token: str


class RefreshUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        refresh_token: str,
        ip: str | None,
        user_agent: str | None,
        audience: str | None = None,
    ) -> RefreshResult:
        if audience is not None and audience not in self._ctx.settings.allowed_token_audiences:
            raise UnauthorizedError("audiencia no permitida")

        provided_hash = self._ctx.token_hasher.hash(refresh_token)
        session = await self._ctx.sessions.get_by_refresh_hash(provided_hash)

        if session is None:
            # Posible reutilización de un refresh ya rotado.
            reused = await self._ctx.sessions.get_by_previous_refresh_hash(provided_hash)
            if reused is not None:
                await self._ctx.sessions.revoke_all_for_user(reused.user_id)
                await audit(
                    self._ctx,
                    event_type="refresh",
                    actor=str(reused.user_id),
                    subject=str(reused.user_id),
                    ip=ip,
                    user_agent=user_agent,
                    outcome="reuse_detected",
                    context={"session": str(reused.id)},
                )
                raise TokenReuseDetectedError("refresh reutilizado; sesiones revocadas")
            await audit(
                self._ctx,
                event_type="refresh",
                actor=None,
                subject=None,
                ip=ip,
                user_agent=user_agent,
                outcome="failure",
                context={},
            )
            raise InvalidTokenError("refresh token inválido")

        if session.revoked_at is not None or ensure_utc(session.refresh_expires_at) <= datetime.now(
            UTC
        ):
            await audit(
                self._ctx,
                event_type="refresh",
                actor=str(session.user_id),
                subject=str(session.user_id),
                ip=ip,
                user_agent=user_agent,
                outcome="failure",
                context={"session": str(session.id)},
            )
            raise InvalidTokenError("refresh token inválido")

        user = await self._ctx.users.get_by_id(session.user_id)
        if user is None:
            raise InvalidTokenError("refresh token inválido")

        # Rotación: el hash actual pasa a ser el "anterior" (detección de reuso).
        new_refresh = self._ctx.secret_generator.generate(48)
        session.previous_refresh_token_hash = session.refresh_token_hash
        session.refresh_token_hash = self._ctx.token_hasher.hash(new_refresh)
        session.touch()
        session.refresh_expires_at = datetime.now(UTC) + timedelta(
            seconds=self._ctx.settings.refresh_token_ttl_seconds
        )
        await self._ctx.sessions.save(session)

        access = self._ctx.token_provider.issue_access_token(
            user_id=user.id,
            session_id=session.id,
            roles=user.roles,
            email_verified=user.email_verified,
            scope="openid profile api:vote",
            ttl_seconds=self._ctx.settings.access_token_ttl_seconds,
            audience=audience,
        )
        await audit(
            self._ctx,
            event_type="refresh",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"session": str(session.id)},
        )
        return RefreshResult(access_token=access, refresh_token=new_refresh)
