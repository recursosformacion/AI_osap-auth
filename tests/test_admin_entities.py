"""Tests de la administración de entidades y pertenencias."""

from __future__ import annotations

import uuid

import pytest

from application.use_cases.admin_entities import (
    admin_add_manager,
    admin_add_membership,
    admin_create_entity,
    admin_remove_manager,
    admin_update_entity,
    admin_decide_membership,
    admin_delete_membership,
    admin_entity_infos,
    admin_set_representative,
)
from application.use_cases.entity_helpers import create_entity
from application.use_cases.register import RegisterUseCase
from domain.exceptions import ForbiddenError
from tests.fakes import make_context


async def _user(ctx, email: str) -> object:
    result = await RegisterUseCase(ctx).execute(
        email=email, password="s3cret-password", ip=None, user_agent=None
    )
    user = await ctx.users.get_by_id(uuid.UUID(str(result.user_id)))
    assert user is not None
    return user


async def test_lista_entidades_con_representante() -> None:
    ctx, _ = make_context()
    owner = await _user(ctx, "owner@example.com")
    entity = await create_entity(
        ctx, user=owner, name="Coral Aurora", kind="coral",
        email="coral@example.com", ip=None, user_agent=None,
    )

    infos = await admin_entity_infos(ctx)

    assert [(item["id"], item["representative_user_id"]) for item in infos] == [
        (str(entity.id), str(owner.id))
    ]


async def test_admin_anade_y_decide_pertenencia() -> None:
    ctx, _ = make_context()
    owner = await _user(ctx, "owner@example.com")
    member = await _user(ctx, "member@example.com")
    entity = await create_entity(
        ctx, user=owner, name="Coral Aurora", kind="coral",
        email="coral@example.com", ip=None, user_agent=None,
    )

    added = await admin_add_membership(
        ctx, user_id=str(member.id), entity_id=str(entity.id), status="pending",
        representative=False, actor=str(owner.id), ip=None, user_agent=None,
    )
    membership = added["memberships"][0]
    assert membership["status"] == "pending"

    decided = await admin_decide_membership(
        ctx, user_id=str(member.id), membership_id=membership["id"], action="approve",
        actor=str(owner.id), ip=None, user_agent=None,
    )
    assert decided["memberships"][0]["status"] == "approved"


async def test_representante_y_baja_protegida() -> None:
    ctx, _ = make_context()
    owner = await _user(ctx, "owner@example.com")
    member = await _user(ctx, "member@example.com")
    entity = await create_entity(
        ctx, user=owner, name="Coral Aurora", kind="coral",
        email="coral@example.com", ip=None, user_agent=None,
    )
    await admin_add_membership(
        ctx, user_id=str(member.id), entity_id=str(entity.id), status="approved",
        representative=False, actor=str(owner.id), ip=None, user_agent=None,
    )
    transferred = await admin_set_representative(
        ctx, entity_id=str(entity.id), user_id=str(member.id),
        actor=str(owner.id), ip=None, user_agent=None,
    )
    rep = next(item for item in transferred["memberships"] if item["is_representative"])
    assert rep["entity_id"] == str(entity.id)

    # Con varios gestores, quitar uno está permitido; el último está protegido.\n    await admin_delete_membership(\n        ctx, user_id=str(member.id), membership_id=rep["id"],\n        actor=str(owner.id), ip=None, user_agent=None,\n    )\n    owner_membership = next(\n        item for item in transferred["memberships"]\n        if item["entity_id"] == str(entity.id) and item["is_manager"]\n    )\n    with pytest.raises(ForbiddenError):\n        await admin_delete_membership(\n            ctx, user_id=str(owner.id), membership_id=owner_membership["id"],\n            actor=str(owner.id), ip=None, user_agent=None,\n        )



async def test_crud_admin_de_entidad_y_gestores() -> None:
    ctx, _ = make_context()
    owner = await _user(ctx, "owner@example.com")
    second = await _user(ctx, "second@example.com")

    created = await admin_create_entity(
        ctx, name="Coral Nueva", kind="coral", email="nueva@example.com",
        manager_user_id=str(owner.id), actor=str(owner.id), ip=None, user_agent=None,
    )
    assert created["name"] == "Coral Nueva"
    assert [item["user_id"] for item in created["managers"]] == [str(owner.id)]

    updated = await admin_update_entity(
        ctx, entity_id=created["id"], name="Coral Renombrada", kind="orquesta",
        email=None, actor=str(owner.id), ip=None, user_agent=None,
    )
    assert updated["name"] == "Coral Renombrada"
    assert updated["kind"] == "orquesta"

    with_two = await admin_add_manager(
        ctx, entity_id=created["id"], user_id=str(second.id),
        actor=str(owner.id), ip=None, user_agent=None,
    )
    assert len(with_two["managers"]) == 2
    with_one = await admin_remove_manager(
        ctx, entity_id=created["id"], user_id=str(owner.id),
        actor=str(second.id), ip=None, user_agent=None,
    )
    assert [item["user_id"] for item in with_one["managers"]] == [str(second.id)]
