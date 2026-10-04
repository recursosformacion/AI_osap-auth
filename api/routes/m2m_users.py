"""Ruta M2M de osap-auth: resolución en lote de nombres visibles (`user_id → name`).

Endpoint de **servicio**, no público: exige un service token con `aud=osap-auth` y el scope
`auth:read_public_names`. Devuelve como máximo `id` + `name`. No crea ni modifica usuarios;
los UUID inexistentes o mal formados se omiten.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_ctx, require_service_scope
from api.schemas import PublicNameItem, PublicUserItem
from application.context import AuthContext
from application.use_cases.m2m_users import (
    ListPublicUsersUseCase,
    LookupPublicNamesUseCase,
)
from domain.exceptions import TooManyIdentifiersError

router = APIRouter(prefix="/auth/m2m", tags=["m2m"])

# Contrato cerrado 2026-10-02: audiencia propia + scope específico (no reutiliza scopes amplios).
AUDIENCE = "osap-auth"
SCOPE = "auth:read_public_names"
MAX_IDS = 500


@router.get(
    "/users",
    response_model=list[PublicNameItem],
    summary="Resuelve nombres visibles por user_id (M2M)",
    description=(
        "Service token con aud=osap-auth y scope auth:read_public_names. `ids` es una lista de "
        "UUID separados por coma (máximo 500). Devuelve solo id + name de los usuarios no "
        "eliminados; los UUID inexistentes o mal formados se omiten."
    ),
)
async def lookup_users(
    ids: str = Query(..., description="UUID separados por coma (máximo 500)"),
    _claims: dict[str, object] = Depends(require_service_scope(SCOPE, AUDIENCE)),
    ctx: AuthContext = Depends(get_ctx),
) -> list[PublicNameItem]:
    parsed: list[uuid.UUID] = []
    for raw in ids.split(","):
        limpio = raw.strip()
        if not limpio:
            continue
        try:
            parsed.append(uuid.UUID(limpio))
        except ValueError:
            continue
    if len(parsed) > MAX_IDS:
        raise TooManyIdentifiersError(f"demasiados ids (máximo {MAX_IDS})")
    result = await LookupPublicNamesUseCase(ctx).execute(parsed)
    return [
        PublicNameItem(
            id=item.id,
            name=item.name,
            nickname=item.nickname,
            nickname_public_consent=item.nickname_public_consent,
        )
        for item in result
    ]


@router.get(
    "/public-users",
    response_model=list[PublicUserItem],
    summary="Lista de usuarios públicos (M2M)",
    description=(
        "Service token con aud=osap-auth y scope auth:read_public_names. Devuelve los usuarios "
        "con consentimiento de cuenta activo (`nickname_public_consent`) y nickname, no "
        "eliminados: fuente de la lista de colaboradores. Solo `id` + `nickname`."
    ),
)
async def list_public_users(
    _claims: dict[str, object] = Depends(require_service_scope(SCOPE, AUDIENCE)),
    ctx: AuthContext = Depends(get_ctx),
) -> list[PublicUserItem]:
    result = await ListPublicUsersUseCase(ctx).execute()
    return [PublicUserItem(id=item.id, nickname=item.nickname) for item in result]
