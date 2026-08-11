"""Ruta OAuth2 client_credentials para tokens de servicio."""

from __future__ import annotations

import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.dependencies import client_ip, client_user_agent, get_ctx
from application.context import AuthContext
from application.use_cases.service_tokens import IssueServiceTokenUseCase

router = APIRouter(tags=["oauth"])


async def _parse_token_request(request: Request) -> dict[str, Any]:
    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        return await request.json()
    # OAuth2 token endpoints usan application/x-www-form-urlencoded (estándar).
    raw = (await request.body()).decode("utf-8")
    return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}


@router.post("/oauth/token", response_model=None)
async def oauth_token(
    request: Request,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    body = await _parse_token_request(request)
    if body.get("grant_type") != "client_credentials":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
    result = await IssueServiceTokenUseCase(ctx).execute(
        client_id=body.get("client_id", ""),
        client_secret=body.get("client_secret", ""),
        requested_scope=body.get("scope", ""),
        ip=ip,
        user_agent=ua,
    )
    return JSONResponse(
        {
            "access_token": result.access_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "scope": result.scope,
        }
    )
