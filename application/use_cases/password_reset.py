"""Caso de uso: recuperación de contraseña."""

from __future__ import annotations

import logging

from application.audit import audit
from application.context import AuthContext
from application.identity_emails import password_reset_email
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.exceptions import InvalidTokenError, RateLimitedError
from domain.services.email_utils import validate_password

logger = logging.getLogger("osap_auth.password_reset")


class RequestPasswordResetUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, email: str, ip: str | None, user_agent: str | None) -> None:
        allowed = await self._ctx.rate_limiter.check_and_increment(
            f"reset_request:{ip or 'unknown'}",
            self._ctx.settings.password_reset_request_per_minute,
            60,
        )
        if not allowed:
            raise RateLimitedError("demasiadas peticiones")

        lookup = self._ctx.email_protector.lookup(email)
        user = await self._ctx.users.get_by_email_lookup(lookup)
        # Timing igualado aunque no exista la cuenta.
        self._ctx.password_hasher.dummy_verify()

        if user is None:
            await audit(
                self._ctx,
                event_type="password.reset.requested",
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
            purpose=TokenPurpose.RESET_PASSWORD,
            token_hash=self._ctx.token_hasher.hash(raw_token),
            ttl_hours=self._ctx.settings.password_reset_token_ttl_hours,
        )
        await self._ctx.tokens.save(token)
        self._send_reset(email, raw_token)
        await audit(
            self._ctx,
            event_type="password.reset.requested",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={},
        )

    def _send_reset(self, email: str, token: str) -> None:
        try:
            self._ctx.email_sender.send(
                password_reset_email(
                    web_base_url=self._ctx.settings.web_base_url,
                    to=email,
                    token=token,
                    ttl_hours=self._ctx.settings.password_reset_token_ttl_hours,
                )
            )
        except Exception as exc:  # noqa: BLE001 — el reset no debe romperse por el correo
            logger.warning("no se pudo enviar el email de recuperación: %s", exc)


class ConfirmPasswordResetUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, token: str, new_password: str, ip: str | None, user_agent: str | None
    ) -> None:
        allowed = await self._ctx.rate_limiter.check_and_increment(
            f"reset_confirm:{ip or 'unknown'}",
            self._ctx.settings.password_reset_confirm_per_minute,
            60,
        )
        if not allowed:
            raise RateLimitedError("demasiadas peticiones")

        validate_password(new_password)
        record = await self._ctx.tokens.get_by_hash(
            self._ctx.token_hasher.hash(token), TokenPurpose.RESET_PASSWORD
        )
        if record is None or record.is_used or record.is_expired:
            raise InvalidTokenError("token de recuperación inválido o caducado")

        user = await self._ctx.users.get_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("token de recuperación inválido")

        # Consumo atómico: bajo doble confirmación concurrente, solo una gana.
        if not await self._ctx.tokens.consume(record.id):
            raise InvalidTokenError("token de recuperación ya utilizado")

        user.password_hash = self._ctx.password_hasher.hash(new_password)
        user.touch()
        await self._ctx.users.save(user)
        # Revocar todas las sesiones tras un reset de contraseña.
        await self._ctx.sessions.revoke_all_for_user(user.id)
        await audit(
            self._ctx,
            event_type="password.reset.confirmed",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={},
        )
