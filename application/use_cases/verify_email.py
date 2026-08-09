"""Casos de uso: verificación de email y reenvío."""

from __future__ import annotations

from application.audit import audit
from application.context import AuthContext
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.entities.user import UserStatus
from domain.exceptions import (
    EmailAlreadyVerifiedError,
    InvalidTokenError,
    RateLimitedError,
)


class VerifyEmailUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, token: str, ip: str | None, user_agent: str | None) -> None:
        record = await self._lookup(token)
        if record is None or record.is_used or record.is_expired:
            await audit(
                self._ctx,
                event_type="email.verify.failed",
                actor=None,
                subject=None,
                ip=ip,
                user_agent=user_agent,
                outcome="failure",
                context={},
            )
            raise InvalidTokenError("token de verificación inválido o caducado")

        user = await self._ctx.users.get_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("token de verificación inválido")
        if user.email_verified:
            raise EmailAlreadyVerifiedError("email ya verificado")

        from datetime import UTC, datetime

        user.email_verified_at = datetime.now(UTC)
        user.status = UserStatus.ACTIVE
        user.touch()
        await self._ctx.users.save(user)
        await self._ctx.tokens.mark_used(record.id)
        await audit(
            self._ctx,
            event_type="email.verified",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={},
        )

    async def _lookup(self, token: str) -> TokenRecord | None:
        return await self._ctx.tokens.get_by_hash(
            self._ctx.token_hasher.hash(token), TokenPurpose.VERIFY_EMAIL
        )


class ResendVerificationUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, email: str, ip: str | None, user_agent: str | None) -> None:
        allowed = await self._ctx.rate_limiter.check_and_increment(
            f"resend:{ip or 'unknown'}",
            self._ctx.settings.resend_verification_per_minute,
            60,
        )
        if not allowed:
            raise RateLimitedError("demasiadas peticiones")

        lookup = self._ctx.email_protector.lookup(email)
        user = await self._ctx.users.get_by_email_lookup(lookup)
        # Respuesta siempre genérica.
        if user is None or user.email_verified:
            await audit(
                self._ctx,
                event_type="email.verify.failed",
                actor=None,
                subject=lookup,
                ip=ip,
                user_agent=user_agent,
                outcome="generic",
                context={},
            )
            return

        raw_token = self._ctx.secret_generator.generate(32)
        token = TokenRecord.new(
            user_id=user.id,
            purpose=TokenPurpose.VERIFY_EMAIL,
            token_hash=self._ctx.token_hasher.hash(raw_token),
            ttl_hours=self._ctx.settings.verification_token_ttl_hours,
        )
        await self._ctx.tokens.save(token)
        await audit(
            self._ctx,
            event_type="email.verify.failed",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="resent",
            context={},
        )
