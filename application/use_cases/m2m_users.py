"""Caso de uso M2M: resolución en lote de nombres visibles (`auth.users.name`).

Contrato cerrado (2026-10-02): `user_id → name`, **solo** `id` + `name` (ni email, ni roles,
ni estado). Es una capacidad de servicio (`aud=osap-auth`, scope `auth:read_public_names`),
no una identidad nueva ni una modificación de usuarios. Los UUID inexistentes simplemente no
aparecen en la respuesta.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from application.context import AuthContext
from domain.entities.user import UserStatus


@dataclass(frozen=True)
class PublicName:
    id: str
    name: str | None
    nickname: str | None = None
    nickname_public_consent: bool = False


@dataclass(frozen=True)
class PublicUser:
    """Entrada de la lista pública de colaboradores: solo id + nickname (nunca email/name)."""

    id: str
    nickname: str


class LookupPublicNamesUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, ids: list[uuid.UUID]) -> list[PublicName]:
        if not ids:
            return []
        users = await self._ctx.users.get_by_ids(ids)
        # `DELETED` no se expone; `ACTIVE`/`DISABLED` sí (la presentación la decide la fachada).
        return [
            PublicName(
                id=str(user.id),
                name=user.name,
                nickname=user.nickname,
                nickname_public_consent=user.nickname_public_consent,
            )
            for user in users
            if user.status is not UserStatus.DELETED
        ]


class ListPublicUsersUseCase:
    """Lista los usuarios publicables (`nickname_public_consent` + nickname, no eliminados).

    Es la fuente de la lista de colaboradores: la fachada (osap-api) decide cómo mostrarlos y
    los cruza con los reconocimientos de osap-support. No expone email, roles ni `name`.
    """

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self) -> list[PublicUser]:
        users = await self._ctx.users.list_public()
        return [
            PublicUser(id=str(user.id), nickname=user.nickname or "")
            for user in users
            if user.nickname
        ]
