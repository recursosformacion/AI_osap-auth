"""Casos de uso: logout y gestión de sesiones."""

from __future__ import annotations

import uuid

from application.audit import audit
from application.context import AuthContext
from domain.exceptions import SessionNotFoundError


class LogoutUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, session_id: uuid.UUID, user_id: uuid.UUID, ip: str | None, user_agent: str | None
    ) -> None:
        session = await self._ctx.sessions.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise SessionNotFoundError("sesión no encontrada")
        await self._ctx.sessions.revoke(session_id)
        await audit(
            self._ctx,
            event_type="logout",
            actor=str(user_id),
            subject=str(user_id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"session": str(session_id)},
        )


class LogoutAllUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, user_id: uuid.UUID, ip: str | None, user_agent: str | None) -> None:
        await self._ctx.sessions.revoke_all_for_user(user_id)
        await audit(
            self._ctx,
            event_type="logout.all",
            actor=str(user_id),
            subject=str(user_id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={},
        )


class ListSessionsUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, user_id: uuid.UUID) -> list[dict[str, object]]:
        sessions = await self._ctx.sessions.list_for_user(user_id)
        return [
            {
                "id": str(s.id),
                "created_at": s.created_at.isoformat(),
                "last_used_at": s.last_used_at.isoformat(),
                "revoked": s.revoked_at is not None,
                "ip": s.ip,
                "user_agent": s.user_agent,
                "device_label": s.device_label,
            }
            for s in sessions
        ]


class RevokeSessionUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, session_id: uuid.UUID, user_id: uuid.UUID, ip: str | None, user_agent: str | None
    ) -> None:
        session = await self._ctx.sessions.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise SessionNotFoundError("sesión no encontrada")
        await self._ctx.sessions.revoke(session_id)
        await audit(
            self._ctx,
            event_type="session.revoked",
            actor=str(user_id),
            subject=str(user_id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"session": str(session_id)},
        )
