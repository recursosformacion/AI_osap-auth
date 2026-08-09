"""Ruta OAuth2 client_credentials para tokens de servicio."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.dependencies import client_ip, client_user_agent, get_ctx
from api.schemas import OAuthTokenRequest
from application.context import AuthContext
from application.use_cases.service_tokens import IssueServiceTokenUseCase

router = APIRouter(tags=["oauth"])


@router.post("/oauth/token", response_model=None)
async def oauth_token(
    body: OAuthTokenRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    if body.grant_type != "client_credentials":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
    result = await IssueServiceTokenUseCase(ctx).execute(
        client_id=body.client_id,
        client_secret=body.client_secret,
        requested_scope=body.scope,
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
