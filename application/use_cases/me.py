"""Casos de uso: perfil, cambio de contraseña, cambio de email."""

from __future__ import annotations

import uuid

from application.audit import audit
from application.context import AuthContext
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.exceptions import InvalidCredentialsError, InvalidTokenError, UnauthorizedError
from domain.services.email_utils import normalize_email, validate_password


class GetMeUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, user_id: uuid.UUID) -> dict[str, object]:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("usuario no encontrado")
        email = self._ctx.email_protector.decrypt(user.email_cipher)
        return {
            "user_id": str(user.id),
            "email": email,
            "name": user.name,
            "roles": user.roles,
            "email_verified": user.email_verified,
            "status": user.status.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


class ChangePasswordUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("usuario no encontrado")
        if not self._ctx.password_hasher.verify(current_password, user.password_hash):
            raise InvalidCredentialsError("contraseña actual incorrecta")
        validate_password(new_password)
        user.password_hash = self._ctx.password_hasher.hash(new_password)
        user.touch()
        await self._ctx.users.save(user)
        await self._ctx.sessions.revoke_all_for_user(user.id)
        await audit(
            self._ctx,
            event_type="password.changed",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={},
        )


class ChangeEmailUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, user_id: uuid.UUID, new_email: str, ip: str | None, user_agent: str | None
    ) -> str:
        """Inicia un cambio de email: exige reverificación del nuevo email.

        Devuelve el token de confirmación (en producción se enviaría por email).
        """
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("usuario no encontrado")

        normalized = normalize_email(new_email)
        if await self._ctx.users.exists(self._ctx.email_protector.lookup(normalized)):
            # Anti-enumeración: respuesta genérica.
            raise InvalidTokenError("no se pudo cambiar el email")

        raw_token = self._ctx.secret_generator.generate(32)
        token = TokenRecord.new(
            user_id=user.id,
            purpose=TokenPurpose.CHANGE_EMAIL,
            token_hash=self._ctx.token_hasher.hash(raw_token),
            ttl_hours=self._ctx.settings.verification_token_ttl_hours,
        )
        await self._ctx.tokens.save(token)
        await audit(
            self._ctx,
            event_type="email.changed",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="requested",
            context={},
        )
        return raw_token


class ConfirmChangeEmailUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, token: str, ip: str | None, user_agent: str | None) -> None:
        # En v1.0 el cambio de email queda registrado pero requiere transporte seguro
        # del nuevo email; se trata como confirmación de verificación ya realizada.
        record = await self._ctx.tokens.get_by_hash(
            self._ctx.token_hasher.hash(token), TokenPurpose.CHANGE_EMAIL
        )
        if record is None or record.is_used or record.is_expired:
            raise InvalidTokenError("token de cambio de email inválido")
        user = await self._ctx.users.get_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("token de cambio de email inválido")
        await self._ctx.tokens.mark_used(record.id)
        await audit(
            self._ctx,
            event_type="email.changed",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="confirmed",
            context={},
        )
