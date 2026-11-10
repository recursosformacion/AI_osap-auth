"""Casos de uso de entidades: listado, solicitudes y edición en la ficha del usuario."""

from __future__ import annotations

import uuid
from typing import Any

from application.audit import audit
from application.context import AuthContext
from application.use_cases.entity_helpers import (
    approve_membership,
    join_entity,
    leave_membership,
    manager_pending_requests,
    reject_membership,
    represent_entity,
)
from application.use_cases.me import GetMeUseCase
from domain.entities.user import UserStatus
from domain.exceptions import InvalidEntityError, UserNotFoundError


class ListEntitiesUseCase:
    """Entidades dadas de alta, para ofrecerlas a futuros usuarios."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self) -> list[dict[str, object]]:
        return [
            {"id": str(entity.id), "name": entity.name, "kind": entity.kind.value}
            for entity in await self._ctx.entities.list_all()
        ]


class ListMyEntityRequestsUseCase:
    """Solicitudes pendientes de las entidades que gestiona el usuario."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, manager_id: uuid.UUID) -> list[dict[str, Any]]:
        return await manager_pending_requests(self._ctx, manager_id)


class DecideEntityRequestUseCase:
    """El gestor aprueba o rechaza una solicitud de incorporación."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        manager_id: uuid.UUID,
        membership_id: uuid.UUID,
        action: str,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, str]:
        if action == "approve":
            membership = await approve_membership(
                self._ctx,
                manager_id=manager_id,
                membership_id=membership_id,
                ip=ip,
                user_agent=user_agent,
            )
        elif action == "reject":
            membership = await reject_membership(
                self._ctx,
                manager_id=manager_id,
                membership_id=membership_id,
                ip=ip,
                user_agent=user_agent,
            )
        else:
            raise InvalidEntityError("decisión inválida")
        return {"message": f"solicitud {membership.status.value}"}


class UpdateMyEntityUseCase:
    """El propio usuario gestiona sus pertenencias desde la ficha de cuenta.

    Acciones:
    - `join`: solicitar pertenecer a `entity_id` (queda pendiente de aprobación).
    - `leave`: dejar de pertenecer a `entity_id`.
    - `represent`: crear una entidad (`entity_name` + `entity_kind`) o actualizar una
      que ya gestiona (`entity_id` + nombre/tipo).
    """

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        user_id: uuid.UUID,
        action: str,
        entity_id: str | None,
        entity_name: str | None,
        entity_kind: str | None,
        entity_email: str | None,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None or user.status == UserStatus.DELETED:
            raise UserNotFoundError("usuario no encontrado")

        if action == "join":
            if not entity_id:
                raise InvalidEntityError("indica la entidad a la que quieres pertenecer")
            await join_entity(
                self._ctx, user=user, entity_id=entity_id, ip=ip, user_agent=user_agent
            )
        elif action == "leave":
            if not entity_id:
                raise InvalidEntityError("indica la entidad que quieres dejar")
            await leave_membership(
                self._ctx, user=user, entity_id=entity_id, ip=ip, user_agent=user_agent
            )
        elif action == "represent":
            await represent_entity(
                self._ctx,
                user=user,
                entity_id=entity_id,
                name=entity_name,
                kind=entity_kind,
                email=entity_email,
                ip=ip,
                user_agent=user_agent,
            )
        else:
            raise InvalidEntityError("acción de entidad inválida")

        user.touch()
        await self._ctx.users.save(user)
        await audit(
            self._ctx,
            event_type="user.entity.changed",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"action": action, "entity_id": entity_id},
        )
        return await GetMeUseCase(self._ctx).execute(user_id=user.id)
