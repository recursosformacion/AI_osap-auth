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
    EntityTakenError,
    ForbiddenError,
    InvalidEntityError,
    MembershipNotFoundError,
    UserNotFoundError,
)
from domain.services.entity import clean_name, normalize_name, validate_email, validate_kind

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


async def _entity_managers(ctx: AuthContext, entity: Entity) -> list[dict[str, Any]]:
    managers: list[dict[str, Any]] = []
    for membership in await ctx.entity_memberships.list_for_entity(entity.id):
        if membership.role != "manager" or membership.status is not MembershipStatus.APPROVED:
            continue
        user = await ctx.users.get_by_id(membership.user_id)
        if user is None:
            continue
        managers.append(
            {
                "user_id": str(user.id),
                "name": user.nickname or user.name,
                "email": None,
            }
        )
    return managers


async def _entity_info(ctx: AuthContext, entity: Entity) -> dict[str, Any]:
    managers = await _entity_managers(ctx, entity)
    representative = next(
        (item for item in managers if item["user_id"] == str(entity.created_by)),
        managers[0] if managers else None,
    )
    return {
        "id": str(entity.id),
        "name": entity.name,
        "kind": entity.kind.value,
        "email": entity.email,
        "representative_user_id": representative["user_id"] if representative else None,
        "representative_name": representative["name"] if representative else None,
        "managers": managers,
    }


async def admin_entity_infos(ctx: AuthContext) -> list[dict[str, Any]]:
    """Entidades con sus gestores, para el mantenimiento del admin."""
    return [await _entity_info(ctx, entity) for entity in await ctx.entities.list_all()]


async def admin_create_entity(
    ctx: AuthContext,
    *,
    name: str,
    kind: str,
    email: str | None,
    manager_user_id: str | None,
    actor: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    """Alta de entidad por el admin, con gestor inicial opcional."""
    cleaned = clean_name(name)
    norm = normalize_name(cleaned)
    if await ctx.entities.get_by_name_norm(norm) is not None:
        raise EntityTakenError("nombre de entidad no disponible")
    clean_email = validate_email(email) if email else None
    if clean_email and await ctx.entities.get_by_email(clean_email) is not None:
        raise EntityTakenError("correo de entidad no disponible")
    manager = await _require_user(ctx, manager_user_id) if manager_user_id else None
    entity = Entity.new(
        name=cleaned,
        name_norm=norm,
        kind=validate_kind(kind),
        created_by=manager.id if manager else None,
        email=clean_email,
    )
    await ctx.entities.save(entity)
    if manager is not None:
        membership = EntityMembership.new(
            entity_id=entity.id,
            user_id=manager.id,
            status=MembershipStatus.APPROVED,
            decided_by=_parse_uuid(actor),
            role="manager",
        )
        await ctx.entity_memberships.save(membership)
    await audit(
        ctx,
        event_type="entity.admin_created",
        actor=actor,
        subject=str(entity.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"kind": entity.kind.value, "manager_user_id": manager_user_id},
    )
    return await _entity_info(ctx, entity)


async def admin_update_entity(
    ctx: AuthContext,
    *,
    entity_id: str,
    name: str | None,
    kind: str | None,
    email: str | None,
    actor: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    entity = await _require_entity(ctx, entity_id)
    if name is not None:
        cleaned = clean_name(name)
        norm = normalize_name(cleaned)
        existing = await ctx.entities.get_by_name_norm(norm)
        if existing is not None and existing.id != entity.id:
            raise EntityTakenError("nombre de entidad no disponible")
        entity.name = cleaned
        entity.name_norm = norm
    if kind is not None:
        entity.kind = validate_kind(kind)
    if email is not None:
        clean_email = validate_email(email) if email.strip() else None
        if clean_email:
            existing_email = await ctx.entities.get_by_email(clean_email)
            if existing_email is not None and existing_email.id != entity.id:
                raise EntityTakenError("correo de entidad no disponible")
        entity.email = clean_email
    entity.touch()
    await ctx.entities.save(entity)
    await audit(
        ctx,
        event_type="entity.admin_updated",
        actor=actor,
        subject=str(entity.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"kind": entity.kind.value},
    )
    return await _entity_info(ctx, entity)


async def admin_add_manager(
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
            role="manager",
        )
    else:
        membership.role = "manager"
        membership.approve(actor_id)
    await ctx.entity_memberships.save(membership)
    if entity.created_by is None:
        entity.created_by = user.id
        entity.touch()
        await ctx.entities.save(entity)
    await audit(
        ctx,
        event_type="entity.manager_added",
        actor=actor,
        subject=str(entity.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"user_id": str(user.id)},
    )
    return await _entity_info(ctx, entity)


async def admin_remove_manager(
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
    membership = await ctx.entity_memberships.get(entity.id, user.id)
    if membership is None or membership.role != "manager":
        raise MembershipNotFoundError("el usuario no es gestor de la entidad")
    remaining = [
        item for item in await _entity_managers(ctx, entity) if item["user_id"] != str(user.id)
    ]
    if not remaining:
        raise ForbiddenError("la entidad debe conservar al menos un gestor")
    membership.role = "member"
    await ctx.entity_memberships.save(membership)
    if entity.created_by == user.id:
        entity.created_by = _parse_uuid(remaining[0]["user_id"])
        entity.touch()
        await ctx.entities.save(entity)
    await audit(
        ctx,
        event_type="entity.manager_removed",
        actor=actor,
        subject=str(entity.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"user_id": str(user.id)},
    )
    return await _entity_info(ctx, entity)


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
    manager: bool = False,
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

    if representative or manager:
        membership.role = "manager"
        membership.approve(actor_id)
        if representative or entity.created_by is None:
            entity.created_by = user.id
            entity.touch()
            await ctx.entities.save(entity)
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
            "manager": manager,
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
    if membership.role == "manager":
        remaining = [
            item
            for item in await _entity_managers(ctx, entity)
            if item["user_id"] != str(user.id)
        ]
        if not remaining:
            raise ForbiddenError("la entidad debe conservar al menos un gestor")
        if entity.created_by == user.id:
            entity.created_by = _parse_uuid(remaining[0]["user_id"])
            entity.touch()
            await ctx.entities.save(entity)
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
            role="manager",
        )
    else:
        membership.role = "manager"
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