"""Administración de entidades y pertenencias (solo rol admin).

Complementa la gestión del representante: un administrador puede añadir o quitar
pertenencias, aprobar/rechazar solicitudes y transferir la representación de una
entidad. Todas las operaciones quedan auditadas.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from application.audit import audit
from application.context import AuthContext
from application.use_cases.admin_users import public_user
from domain.entities.entity import Entity
from domain.entities.entity_membership import EntityMembership, MembershipStatus
from domain.entities.user import User
from domain.exceptions import (
    EntityNotFoundError,
    ForbiddenError,
    InvalidEntityError,
    MembershipNotFoundError,
    UserNotFoundError,
)

MembershipAction = Literal["approved", "pending", "rejected"]


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise InvalidEntityError("identificador inválido") from None


async def _require_user(ctx: AuthContext, user_id: str) -> User:
    user = await ctx.users.get_by_id(_parse_uuid(user_id))
    if user is None:
        raise UserNotFoundError("usuario no encontrado")
    return user


async def _require_entity(ctx: AuthContext, entity_id: str) -> Entity:
    entity = await ctx.entities.get_by_id(_parse_uuid(entity_id))
    if entity is None:
        raise EntityNotFoundError("entidad no encontrada")
    return entity


async def _require_membership(
    ctx: AuthContext, membership_id: str, user_id: uuid.UUID
) -> EntityMembership:
    membership = await ctx.entity_memberships.get_by_id(_parse_uuid(membership_id))
    if membership is None or membership.user_id != user_id:
        raise MembershipNotFoundError("pertenencia no encontrada")
    return membership


async def admin_entity_infos(ctx: AuthContext) -> list[dict[str, Any]]:
    """Entidades con su representante, para el selector del admin."""
    result: list[dict[str, Any]] = []
    for entity in await ctx.entities.list_all():
        representative = (
            await ctx.users.get_by_id(entity.created_by) if entity.created_by else None
        )
        result.append(
            {
                "id": str(entity.id),
                "name": entity.name,
                "kind": entity.kind.value,
                "email": entity.email,
                "representative_user_id": (
                    str(representative.id) if representative is not None else None
                ),
                "representative_name": (
                    representative.nickname or representative.name
                    if representative is not None
                    else None
                ),
            }
        )
    return result


async def admin_add_membership(
    ctx: AuthContext,
    *,
    user_id: str,
    entity_id: str,
    status: MembershipAction,
    representative: bool,
    actor: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    user = await _require_user(ctx, user_id)
    entity = await _require_entity(ctx, entity_id)
    actor_id = _parse_uuid(actor)
    membership = await ctx.entity_memberships.get(entity.id, user.id)
    if membership is None:
        membership = EntityMembership.new(
            entity_id=entity.id,
            user_id=user.id,
            status=MembershipStatus(status),
            decided_by=actor_id if status != "pending" else None,
        )
    elif status == "approved":
        membership.approve(actor_id)
    elif status == "rejected":
        membership.reject(actor_id)
    else:
        membership.re_request()

    if representative:
        entity.created_by = user.id
        entity.touch()
        await ctx.entities.save(entity)
        membership.approve(actor_id)
    await ctx.entity_memberships.save(membership)
    await audit(
        ctx,
        event_type="membership.admin_added",
        actor=actor,
        subject=str(user.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={
            "entity_id": str(entity.id),
            "membership_id": str(membership.id),
            "status": membership.status.value,
            "representative": representative,
        },
    )
    return await public_user(ctx, user)


async def admin_delete_membership(
    ctx: AuthContext,
    *,
    user_id: str,
    membership_id: str,
    actor: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    user = await _require_user(ctx, user_id)
    membership = await _require_membership(ctx, membership_id, user.id)
    entity = await ctx.entities.get_by_id(membership.entity_id)
    if entity is None:
        raise EntityNotFoundError("entidad no encontrada")
    if entity.created_by == user.id:
        raise ForbiddenError("transfiere la representación antes de quitar la pertenencia")
    await ctx.entity_memberships.delete(membership.id)
    await audit(
        ctx,
        event_type="membership.admin_removed",
        actor=actor,
        subject=str(user.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"entity_id": str(entity.id), "membership_id": str(membership.id)},
    )
    return await public_user(ctx, user)


async def admin_decide_membership(
    ctx: AuthContext,
    *,
    user_id: str,
    membership_id: str,
    action: Literal["approve", "reject"],
    actor: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    user = await _require_user(ctx, user_id)
    membership = await _require_membership(ctx, membership_id, user.id)
    actor_id = _parse_uuid(actor)
    if action == "approve":
        membership.approve(actor_id)
    else:
        entity = await ctx.entities.get_by_id(membership.entity_id)
        if entity is not None and entity.created_by == user.id:
            raise ForbiddenError("transfiere la representación antes de rechazar la pertenencia")
        membership.reject(actor_id)
    await ctx.entity_memberships.save(membership)
    await audit(
        ctx,
        event_type="membership.admin_decided",
        actor=actor,
        subject=str(user.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={
            "entity_id": str(membership.entity_id),
            "membership_id": str(membership.id),
            "status": membership.status.value,
        },
    )
    return await public_user(ctx, user)


async def admin_set_representative(
    ctx: AuthContext,
    *,
    entity_id: str,
    user_id: str,
    actor: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    entity = await _require_entity(ctx, entity_id)
    user = await _require_user(ctx, user_id)
    actor_id = _parse_uuid(actor)
    membership = await ctx.entity_memberships.get(entity.id, user.id)
    if membership is None:
        membership = EntityMembership.new(
            entity_id=entity.id,
            user_id=user.id,
            status=MembershipStatus.APPROVED,
            decided_by=actor_id,
        )
    else:
        membership.approve(actor_id)
    await ctx.entity_memberships.save(membership)
    entity.created_by = user.id
    entity.touch()
    await ctx.entities.save(entity)
    await audit(
        ctx,
        event_type="entity.representative_changed",
        actor=actor,
        subject=str(user.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"entity_id": str(entity.id)},
    )
    return await public_user(ctx, user)