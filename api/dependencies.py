"""Dependencias de la API de osap-auth."""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import Depends, Request

from application.context import AuthContext
from domain.exceptions import UnauthorizedError


def get_ctx(request: Request) -> AuthContext:
    ctx: AuthContext = request.app.state.ctx
    return ctx


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def client_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise UnauthorizedError("credenciales requeridas")
    return auth[7:].strip()


def current_user(request: Request, ctx: AuthContext = Depends(get_ctx)) -> dict[str, Any]:
    token = _bearer_token(request)
    try:
        return ctx.token_provider.verify_access_token(
            token, expected_audience=ctx.settings.audience
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedError("token inválido o caducado") from None


def require_role(role: str) -> Any:
    """Dependency factory: exige un rol en el access token."""

    def _dep(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        roles = user.get("roles", [])
        if role not in roles:
            from domain.exceptions import ForbiddenError

            raise ForbiddenError("sin autorización")
        return user

    return _dep
