"""Operaciones compartidas de entidades y pertenencias (solicitud, aprobación, ficha)."""

from __future__ import annotations

import uuid
from typing import Any

from application.audit import audit
from application.context import AuthContext
from application.identity_emails import (
    membership_approved_email,
    membership_rejected_email,
    membership_request_email,
)
from domain.entities.entity import Entity
from domain.entities.entity_membership import EntityMembership, MembershipStatus
from domain.entities.user import User
from domain.exceptions import (
    EntityNotFoundError,
    EntityTakenError,
    ForbiddenError,
    InvalidEntityError,
    MembershipAlreadyDecidedError,
    MembershipNotFoundError,
)
from domain.ports.email import EmailMessage
from domain.services.entity import clean_name, normalize_name, validate_kind


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise InvalidEntityError("identificador inválido") from None


def _decrypt_email(ctx: AuthContext, user: User) -> str:
    return ctx.email_protector.decrypt(user.email_cipher) if user.email_cipher else ""


def _nickname(user: User) -> str:
    return user.nickname or user.name or "un usuario"


def _send_best_effort(ctx: AuthContext, message: EmailMessage) -> None:
    """Un fallo de correo no debe tumbar la operación de negocio."""
    try:
        ctx.email_sender.send(message)
    except Exception:  # noqa: BLE001
        return


async def membership_infos(ctx: AuthContext, user: User) -> list[dict[str, Any]]:
    """Pertenecimientos del usuario (pendientes, aprobados y rechazados) para `GET /me`."""
    infos: list[dict[str, Any]] = []
    for membership in await ctx.entity_memberships.list_for_user(user.id):
        entity = await ctx.entities.get_by_id(membership.entity_id)
        if entity is None:
            continue
        infos.append(
            {
                "id": str(membership.id),
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "entity_kind": entity.kind.value,
                "status": membership.status.value,
                "is_representative": entity.created_by == user.id,
                "requested_at": membership.requested_at.isoformat(),
                "decided_at": (
                    membership.decided_at.isoformat() if membership.decided_at else None
                ),
            }
        )
    return infos


async def create_entity(
    ctx: AuthContext,
    *,
    user: User,
    name: str,
    kind: str,
    ip: str | None,
    user_agent: str | None,
) -> Entity:
    """Crea una entidad; el creador queda como representante y miembro aprobado."""
    cleaned = clean_name(name)
    norm = normalize_name(cleaned)
    if await ctx.entities.get_by_name_norm(norm) is not None:
        raise EntityTakenError("nombre de entidad no disponible")
    entity = Entity.new(
        name=cleaned,
        name_norm=norm,
        kind=validate_kind(kind),
        created_by=user.id,
    )
    await ctx.entities.save(entity)
    membership = EntityMembership.new(
        entity_id=entity.id,
        user_id=user.id,
        status=MembershipStatus.APPROVED,
        decided_by=user.id,
    )
    await ctx.entity_memberships.save(membership)
    await audit(
        ctx,
        event_type="entity.created",
        actor=str(user.id),
        subject=str(user.id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={"entity_id": str(entity.id), "kind": entity.kind.value},
    )
    return entity


async def request_membership(
    ctx: AuthContext,
    *,
    user: User,
    entity: Entity,
    ip: str | None,
    user_agent: str | None,
) -> EntityMembership:
    """Solicita pertenecer a una entidad. Queda `pending` hasta que el gestor decida."""
    existing = await ctx.entity_memberships.get(entity.id, user.id)
    if existing is not None:
        if existing.status is MembershipStatus.APPROVED:
            return existing
        if existing.status is MembershipStatus.REJECTED:
            existing.re_request()
            await ctx.entity_memberships.save(existing)
            await _audit_membership(
                ctx, "membership.requested", user, entity, existing, ip, user_agent
            )
            await _notify_manager(ctx, user, entity)
            return existing
        return existing

    membership = EntityMembership.new(
        entity_id=entity.id,
        user_id=user.id,
        status=MembershipStatus.PENDING,
    )
    await ctx.entity_memberships.save(membership)
    await _audit_membership(ctx, "membership.requested", user, entity, membership, ip, user_agent)
    await _notify_manager(ctx, user, entity)
    return membership


async def approve_membership(
    ctx: AuthContext,
    *,
    manager_id: uuid.UUID,
    membership_id: uuid.UUID,
    ip: str | None,
    user_agent: str | None,
) -> EntityMembership:
    membership, entity = await _manager_membership(ctx, manager_id, membership_id)
    if membership.status is not MembershipStatus.PENDING:
        raise MembershipAlreadyDecidedError("la solicitud ya fue decidida")
    membership.approve(manager_id)
    await ctx.entity_memberships.save(membership)
    await _audit_membership(
        ctx, "membership.approved", None, entity, membership, ip, user_agent, actor=manager_id
    )
    await _notify_decision(ctx, membership, entity, approved=True)
    return membership


async def reject_membership(
    ctx: AuthContext,
    *,
    manager_id: uuid.UUID,
    membership_id: uuid.UUID,
    ip: str | None,
    user_agent: str | None,
) -> EntityMembership:
    membership, entity = await _manager_membership(ctx, manager_id, membership_id)
    if membership.status is not MembershipStatus.PENDING:
        raise MembershipAlreadyDecidedError("la solicitud ya fue decidida")
    membership.reject(manager_id)
    await ctx.entity_memberships.save(membership)
    await _audit_membership(
        ctx, "membership.rejected", None, entity, membership, ip, user_agent, actor=manager_id
    )
    await _notify_decision(ctx, membership, entity, approved=False)
    return membership


async def join_entity(
    ctx: AuthContext,
    *,
    user: User,
    entity_id: str,
    ip: str | None,
    user_agent: str | None,
) -> EntityMembership:
    """Solicita pertenecer a una entidad existente (queda pendiente de aprobación)."""
    entity = await ctx.entities.get_by_id(_parse_uuid(entity_id))
    if entity is None:
        raise EntityNotFoundError("entidad no encontrada")
    return await request_membership(ctx, user=user, entity=entity, ip=ip, user_agent=user_agent)


async def leave_membership(
    ctx: AuthContext,
    *,
    user: User,
    entity_id: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    entity_uuid = _parse_uuid(entity_id)
    membership = await ctx.entity_memberships.get(entity_uuid, user.id)
    if membership is None:
        raise MembershipNotFoundError("no perteneces a esa entidad")
    entity = await ctx.entities.get_by_id(entity_uuid)
    await ctx.entity_memberships.delete(membership.id)
    if entity is not None:
        await _audit_membership(ctx, "membership.left", user, entity, membership, ip, user_agent)


async def represent_entity(
    ctx: AuthContext,
    *,
    user: User,
    entity_id: str | None,
    name: str | None,
    kind: str | None,
    ip: str | None,
    user_agent: str | None,
) -> Entity:
    """Crea una entidad nueva o actualiza una que el usuario gestiona."""
    if entity_id:
        entity = await ctx.entities.get_by_id(_parse_uuid(entity_id))
        if entity is None:
            raise EntityNotFoundError("entidad no encontrada")
        if entity.created_by != user.id:
            raise ForbiddenError("no gestionas esa entidad")
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
        entity.touch()
        await ctx.entities.save(entity)
        await audit(
            ctx,
            event_type="entity.updated",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"entity_id": str(entity.id), "kind": entity.kind.value},
        )
        return entity

    if not name or not kind:
        raise InvalidEntityError("indica el nombre y el tipo de la entidad que representas")
    return await create_entity(ctx, user=user, name=name, kind=kind, ip=ip, user_agent=user_agent)


async def apply_onboarding_entity(
    ctx: AuthContext,
    *,
    user: User,
    entity_id: str | None,
    entity_name: str | None,
    entity_kind: str | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Alta: representar una entidad nueva o solicitar pertenecer a una existente."""
    if entity_name and entity_id:
        raise InvalidEntityError("elige representar una entidad nueva o pertenecer a una existente")
    if entity_name:
        await create_entity(
            ctx, user=user, name=entity_name, kind=entity_kind or "", ip=ip, user_agent=user_agent
        )
        return
    if entity_id:
        entity = await ctx.entities.get_by_id(_parse_uuid(entity_id))
        if entity is None:
            raise EntityNotFoundError("entidad no encontrada")
        await request_membership(ctx, user=user, entity=entity, ip=ip, user_agent=user_agent)


async def manager_pending_requests(
    ctx: AuthContext, manager_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Solicitudes pendientes de las entidades gestionadas por el usuario."""
    result: list[dict[str, Any]] = []
    for membership in await ctx.entity_memberships.list_pending_for_manager(manager_id):
        entity = await ctx.entities.get_by_id(membership.entity_id)
        user = await ctx.users.get_by_id(membership.user_id)
        if entity is None or user is None:
            continue
        result.append(
            {
                "id": str(membership.id),
                "entity_id": str(entity.id),
                "entity_name": entity.name,
                "entity_kind": entity.kind.value,
                "user_id": str(user.id),
                "nickname": user.nickname,
                "name": user.name,
                "requested_at": membership.requested_at.isoformat(),
            }
        )
    return result


async def _manager_membership(
    ctx: AuthContext, manager_id: uuid.UUID, membership_id: uuid.UUID
) -> tuple[EntityMembership, Entity]:
    membership = await ctx.entity_memberships.get_by_id(membership_id)
    if membership is None:
        raise MembershipNotFoundError("solicitud no encontrada")
    entity = await ctx.entities.get_by_id(membership.entity_id)
    if entity is None:
        raise EntityNotFoundError("entidad no encontrada")
    if entity.created_by != manager_id:
        raise ForbiddenError("no gestionas esa entidad")
    return membership, entity


async def _notify_manager(ctx: AuthContext, user: User, entity: Entity) -> None:
    if entity.created_by is None or entity.created_by == user.id:
        return
    manager = await ctx.users.get_by_id(entity.created_by)
    if manager is None:
        return
    email = _decrypt_email(ctx, manager)
    if not email:
        return
    _send_best_effort(
        ctx,
        membership_request_email(
            web_base_url=ctx.settings.web_base_url,
            to=email,
            entity_name=entity.name,
            nickname=_nickname(user),
        ),
    )


async def _notify_decision(
    ctx: AuthContext, membership: EntityMembership, entity: Entity, *, approved: bool
) -> None:
    user = await ctx.users.get_by_id(membership.user_id)
    if user is None:
        return
    email = _decrypt_email(ctx, user)
    if not email:
        return
    template = membership_approved_email if approved else membership_rejected_email
    _send_best_effort(
        ctx,
        template(
            web_base_url=ctx.settings.web_base_url,
            to=email,
            entity_name=entity.name,
        ),
    )


async def _audit_membership(
    ctx: AuthContext,
    event_type: str,
    user: User | None,
    entity: Entity,
    membership: EntityMembership,
    ip: str | None,
    user_agent: str | None,
    *,
    actor: uuid.UUID | None = None,
) -> None:
    actor_id = actor or (user.id if user is not None else None)
    await audit(
        ctx,
        event_type=event_type,
        actor=str(actor_id) if actor_id else None,
        subject=str(membership.user_id),
        ip=ip,
        user_agent=user_agent,
        outcome="success",
        context={
            "entity_id": str(entity.id),
            "membership_id": str(membership.id),
            "status": membership.status.value,
        },
    )
