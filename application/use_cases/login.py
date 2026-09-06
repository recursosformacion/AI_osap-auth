"""Caso de uso: login."""

from __future__ import annotations

from dataclasses import dataclass

from application.audit import audit
from application.context import AuthContext
from domain.entities.session import Session
from domain.entities.user import UserStatus
from domain.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    RateLimitedError,
    UnauthorizedError,
)


@dataclass
class LoginResult:
    access_token: str
    refresh_token: str
    user_id: str
    roles: list[str]
    email_verified: bool


class LoginUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        email: str,
        password: str,
        ip: str | None,
        user_agent: str | None,
        audience: str | None = None,
    ) -> LoginResult:
        if audience is not None and audience not in self._ctx.settings.allowed_token_audiences:
            raise UnauthorizedError("audiencia no permitida")

        allowed = await self._ctx.rate_limiter.check_and_increment(
            f"login:{ip or 'unknown'}",
            self._ctx.settings.login_per_minute,
            60,
        )
        if not allowed:
            raise RateLimitedError("demasiadas peticiones")

        lookup = self._ctx.email_protector.lookup(email)
        user = await self._ctx.users.get_by_email_lookup(lookup)
        if user is None:
            # Timing igualado: verificación ficticia para no enumerar.
            self._ctx.password_hasher.dummy_verify()
            await audit(
                self._ctx,
                event_type="login.failed",
                actor=None,
                subject=lookup,
                ip=ip,
                user_agent=user_agent,
                outcome="failure",
                context={},
            )
            raise InvalidCredentialsError("credenciales inválidas")

        if not self._ctx.password_hasher.verify(password, user.password_hash):
            await audit(
                self._ctx,
                event_type="login.failed",
                actor=str(user.id),
                subject=str(user.id),
                ip=ip,
                user_agent=user_agent,
                outcome="failure",
                context={},
            )
            raise InvalidCredentialsError("credenciales inválidas")

        if user.status in (UserStatus.DISABLED, UserStatus.DELETED):
            raise AccountDisabledError("cuenta no disponible")

        raw_refresh = self._ctx.secret_generator.generate(48)
        session = Session.new(
            user_id=user.id,
            refresh_token_hash=self._ctx.token_hasher.hash(raw_refresh),
            refresh_ttl_seconds=self._ctx.settings.refresh_token_ttl_seconds,
            ip=ip,
            user_agent=user_agent,
        )
        await self._ctx.sessions.save(session)

        scope = "openid profile api:vote"
        access = self._ctx.token_provider.issue_access_token(
            user_id=user.id,
            session_id=session.id,
            roles=user.roles,
            email_verified=user.email_verified,
            scope=scope,
            ttl_seconds=self._ctx.settings.access_token_ttl_seconds,
            audience=audience,
        )
        await audit(
            self._ctx,
            event_type="login",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"session": str(session.id)},
        )
        return LoginResult(
            access_token=access,
            refresh_token=raw_refresh,
            user_id=str(user.id),
            roles=user.roles,
            email_verified=user.email_verified,
        )
