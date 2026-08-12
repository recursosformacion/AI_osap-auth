"""Rutas del login social (upstream): inicio y callback de proveedores externos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from api.dependencies import client_ip, client_user_agent, get_ctx
from application.context import AuthContext
from application.use_cases.social_login import (
    SocialLoginCallbackUseCase,
    SocialLoginStartUseCase,
)
from domain.exceptions import OAuthError

router = APIRouter(tags=["social"])


@router.get("/auth/oauth/providers")
async def social_providers(ctx: AuthContext = Depends(get_ctx)) -> dict[str, list[str]]:
    enabled = [name for name, on in ctx.settings.social_providers_enabled.items() if on]
    return {"providers": enabled}


@router.get("/auth/oauth/{provider}", response_model=None)
async def social_start(
    provider: str,
    request: Request,
    ctx: AuthContext = Depends(get_ctx),
) -> JSONResponse | RedirectResponse:
    params: dict[str, str] = {k: v for k, v in request.query_params.items()}
    try:
        authorize_url = await SocialLoginStartUseCase(ctx).execute(provider=provider, params=params)
    except OAuthError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": exc.error, "error_description": exc.error_description},
        )
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/auth/oauth/{provider}/callback", response_model=None)
async def social_callback(
    provider: str,
    request: Request,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse | RedirectResponse:
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    if not code or not state:
        return JSONResponse(status_code=400, content={"error": "invalid_request"})
    try:
        result = await SocialLoginCallbackUseCase(ctx).execute(
            provider=provider, code=code, state_token=state, ip=ip, user_agent=ua
        )
    except OAuthError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": exc.error, "error_description": exc.error_description},
        )
    return RedirectResponse(result.redirect_uri, status_code=302)
