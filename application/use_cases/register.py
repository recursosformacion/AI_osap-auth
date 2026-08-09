"""Caso de uso: registro de usuario."""

from __future__ import annotations

from dataclasses import dataclass

from application.audit import audit
from application.context import AuthContext
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.entities.user import User
from domain.exceptions import RateLimitedError
from domain.services.email_utils import normalize_email, validate_password


@dataclass
class RegisterResult:
    created: bool
    user_id: str | None = None
    verification_token: str | None = None


class RegisterUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        email: str,
        password: str,
        ip: str | None,
        user_agent: str | None,
        name: str | None = None,
    ) -> RegisterResult:
        allowed = await self._ctx.rate_limiter.check_and_increment(
            f"register:{ip or 'unknown'}",
            self._ctx.settings.register_per_minute,
            60,
        )
        if not allowed:
            raise RateLimitedError("demasiadas peticiones")

        validate_password(password)
        normalized = normalize_email(email)
        # Hash siempre (coste Argon2) para no filtrar por tiempo si existe o no.
        password_hash = self._ctx.password_hasher.hash(password)
        lookup = self._ctx.email_protector.lookup(normalized)

        if await self._ctx.users.exists(lookup):
            # Anti-enumeración: respuesta genérica, sin revelar existencia.
            await audit(
                self._ctx,
                event_type="register",
                actor=None,
                subject=lookup,
                ip=ip,
                user_agent=user_agent,
                outcome="generic",
                context={},
            )
            return RegisterResult(created=False)

        cipher = self._ctx.email_protector.encrypt(normalized)
        clean_name = (name or "").strip() or None
        user = User.new(
            email_lookup=lookup,
            email_cipher=cipher,
            password_hash=password_hash,
            key_version=self._ctx.settings.key_version,
            name=clean_name,
        )
        await self._ctx.users.save(user)

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
            event_type="register",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"verified": False},
        )
        return RegisterResult(created=True, user_id=str(user.id), verification_token=raw_token)
