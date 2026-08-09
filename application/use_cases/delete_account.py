"""Caso de uso: borrado de cuenta (GDPR) + evento user.deleted."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from application.audit import audit
from application.context import AuthContext
from domain.entities.user import UserStatus


class DeleteAccountUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, user_id: uuid.UUID, ip: str | None, user_agent: str | None) -> None:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            return

        # Invalidar sesiones y tokens de un solo uso de la cuenta.
        await self._ctx.sessions.revoke_all_for_user(user.id)

        # Borrado lógico: se mantiene el identificador y el estado para trazabilidad,
        # se eliminan credenciales y datos personales recuperables.
        user.status = UserStatus.DELETED
        user.email_verified_at = None
        user.email_cipher = b""  # se pierde la PII recuperable
        user.email_lookup = f"deleted-{user.id}"  # deja de resolver por email
        user.password_hash = ""  # no hay credencial utilizable
        user.touch()
        await self._ctx.users.save(user)

        deleted_at = datetime.now(UTC).isoformat()
        await audit(
            self._ctx,
            event_type="user.deleted",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"deleted_at": deleted_at},
        )
        # Emitir el evento para los suscriptores (osap-api anonimiza los votos).
        await self._ctx.events.publish_user_deleted(user.id, deleted_at)
