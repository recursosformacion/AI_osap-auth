"""Ruta OAuth2 token: client_credentials (servicio) y flujo OIDC (authorization_code/refresh)."""

from __future__ import annotations

import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.dependencies import client_ip, client_user_agent, get_ctx
from application.context import AuthContext
from application.use_cases.oidc_token import (
    ExchangeAuthorizationCodeUseCase,
    RefreshTokenGrantUseCase,
    TokenResult,
)
from application.use_cases.service_tokens import IssueServiceTokenUseCase
from domain.exceptions import OAuthClientNotFoundError, OAuthError

router = APIRouter(tags=["oauth"])


async def _parse_token_request(request: Request) -> dict[str, Any]:
    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        return await request.json()
    # OAuth2 token endpoints usan application/x-www-form-urlencoded (estándar).
    raw = (await request.body()).decode("utf-8")
    return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}


def _error_response(exc: OAuthError | OAuthClientNotFoundError) -> JSONResponse:
    if isinstance(exc, OAuthClientNotFoundError):
        return JSONResponse(
            status_code=400, content={"error": "invalid_client", "error_description": str(exc)}
        )
    return JSONResponse(
        status_code=400,
        content={"error": exc.error, "error_description": exc.error_description},
    )


@router.post("/oauth/token", response_model=None)
async def oauth_token(
    request: Request,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    body = await _parse_token_request(request)
    grant_type = body.get("grant_type", "")
    result: TokenResult

    try:
        if grant_type == "authorization_code":
            result = await ExchangeAuthorizationCodeUseCase(ctx).execute(
                code=body.get("code", ""),
                code_verifier=body.get("code_verifier", ""),
                redirect_uri=body.get("redirect_uri", ""),
                client_id=body.get("client_id", ""),
                client_secret=body.get("client_secret", ""),
                ip=ip,
                user_agent=ua,
            )
        elif grant_type == "refresh_token":
            result = await RefreshTokenGrantUseCase(ctx).execute(
                refresh_token=body.get("refresh_token", ""),
                client_id=body.get("client_id", ""),
                client_secret=body.get("client_secret", ""),
                ip=ip,
                user_agent=ua,
            )
        elif grant_type == "client_credentials":
            service = await IssueServiceTokenUseCase(ctx).execute(
                client_id=body.get("client_id", ""),
                client_secret=body.get("client_secret", ""),
                requested_scope=body.get("scope", ""),
                ip=ip,
                user_agent=ua,
            )
            return JSONResponse(
                {
                    "access_token": service.access_token,
                    "token_type": service.token_type,
                    "expires_in": service.expires_in,
                    "scope": service.scope,
                }
            )
        else:
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
    except (OAuthError, OAuthClientNotFoundError) as exc:
        return _error_response(exc)

    return JSONResponse(
        {
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "scope": result.scope,
        }
    )
