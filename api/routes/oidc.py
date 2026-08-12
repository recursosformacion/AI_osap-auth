"""Rutas OIDC de osap-auth: discovery, authorize y complete.

osap-auth actúa como Identity Provider (IdP): osap-api y otros servicios bajo
`*.openmusicrepository.com` actúan como relying parties (Authorization Code + PKCE).
"""

from __future__ import annotations

import urllib.parse
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from api.dependencies import current_user, get_ctx
from application.context import AuthContext
from application.use_cases.oidc_authorize import (
    CompleteAuthorizationUseCase,
    ValidateAuthorizeRequestUseCase,
)
from domain.exceptions import OAuthClientNotFoundError, OAuthError

router = APIRouter(tags=["oidc"])

ALGS = ["RS256"]
SCOPES_SUPPORTED = ["openid", "profile", "email"]


def _public_origin(ctx: AuthContext) -> str:
    return f"{ctx.settings.public_base_url.rstrip('/')}{ctx.settings.public_path_prefix}"


@router.get("/.well-known/openid-configuration")
async def openid_configuration(ctx: AuthContext = Depends(get_ctx)) -> dict[str, Any]:
    origin = _public_origin(ctx)
    return {
        "issuer": ctx.settings.effective_issuer,
        "authorization_endpoint": f"{origin}/auth/authorize",
        "token_endpoint": f"{origin}/oauth/token",
        "jwks_uri": f"{origin}/auth/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ALGS,
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": SCOPES_SUPPORTED,
    }


class AuthorizeCompleteRequest(BaseModel):
    client_id: str
    redirect_uri: str
    response_type: str = "code"
    scope: str = "openid profile"
    state: str | None = None
    nonce: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = "S256"


@router.get("/auth/authorize", response_model=None)
async def authorize(
    request: Request, ctx: AuthContext = Depends(get_ctx)
) -> JSONResponse | RedirectResponse:
    params: dict[str, str] = {k: v for k, v in request.query_params.items()}
    try:
        auth_request = await ValidateAuthorizeRequestUseCase(ctx).execute(params)
    except OAuthClientNotFoundError as exc:
        return JSONResponse(
            status_code=400, content={"error": _error_code(exc), "error_description": str(exc)}
        )
    except OAuthError as exc:
        return _error_response(exc)
    return RedirectResponse(auth_request.login_url, status_code=302)


@router.post("/auth/authorize/complete", response_model=None)
async def authorize_complete(
    body: AuthorizeCompleteRequest,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
) -> JSONResponse:
    params = {
        "client_id": body.client_id,
        "redirect_uri": body.redirect_uri,
        "response_type": body.response_type,
        "scope": body.scope,
        "state": body.state or "",
        "nonce": body.nonce or "",
        "code_challenge": body.code_challenge or "",
        "code_challenge_method": body.code_challenge_method or "S256",
    }
    try:
        auth_request = await ValidateAuthorizeRequestUseCase(ctx).execute(params)
    except OAuthClientNotFoundError as exc:
        return JSONResponse(
            status_code=400, content={"error": _error_code(exc), "error_description": str(exc)}
        )
    except OAuthError as exc:
        return _error_json(exc)
    result = await CompleteAuthorizationUseCase(ctx).execute(auth_request, uuid.UUID(user["sub"]))
    return JSONResponse(
        {
            "redirect_uri": result.redirect_uri,
            "code": result.code,
            "state": result.state,
        }
    )


def _error_code(exc: OAuthClientNotFoundError | OAuthError) -> str:
    if isinstance(exc, OAuthError):
        return exc.error
    return exc.error


def _error_json(exc: OAuthError) -> JSONResponse:
    return JSONResponse(
        status_code=400, content={"error": exc.error, "error_description": exc.error_description}
    )


def _error_response(exc: OAuthError) -> JSONResponse | RedirectResponse:
    content = {"error": exc.error, "error_description": exc.error_description}
    if exc.redirect_uri:
        parts = list(urllib.parse.urlparse(exc.redirect_uri))
        query = urllib.parse.parse_qs(parts[4])
        query["error"] = [exc.error]
        if exc.error_description:
            query["error_description"] = [exc.error_description]
        if exc.state:
            query["state"] = [exc.state]
        parts[4] = urllib.parse.urlencode(query, doseq=True)
        return RedirectResponse(urllib.parse.urlunparse(parts), status_code=302)
    return JSONResponse(status_code=400, content=content)
