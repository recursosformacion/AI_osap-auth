"""Rutas de JWKS y versión del contrato."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import get_ctx
from application.context import AuthContext

router = APIRouter(tags=["system"])


@router.get("/auth/.well-known/jwks.json")
async def jwks(ctx: AuthContext = Depends(get_ctx)) -> dict[str, Any]:
    return ctx.token_provider.jwks()


@router.get("/auth/version")
async def version() -> dict[str, str]:
    return {"contract": "osap-auth-v1", "version": "1.0"}
