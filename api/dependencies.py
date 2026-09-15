"""Dependencias de la API de osap-auth."""

from __future__ import annotations

import uuid
from typing import Any

import jwt
from fastapi import Depends, Request

from application.context import AuthContext
from domain.entities.user import UserStatus
from domain.exceptions import ForbiddenError, UnauthorizedError


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
    """Dependency factory: exige un rol, con la BD de usuarios como autoridad.

    El claim `roles` del token es una **foto del momento de emisión**. Si la cuenta se
    promovió (o degradó) después, el token sigue siendo válido pero con roles obsoletos: el
    usuario veía "sin autorización" en los endpoints admin pese a ser admin en la BD. El
    camino rápido es el token; si no trae el rol, se comprueba el estado actual del usuario.
    """

    async def _dep(
        user: dict[str, Any] = Depends(current_user),
        ctx: AuthContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        if role in (user.get("roles") or []):
            return user
        try:
            user_id = uuid.UUID(str(user.get("sub") or ""))
        except ValueError:
            raise ForbiddenError("sin autorización") from None
        record = await ctx.users.get_by_id(user_id)
        if record is None or record.status in (UserStatus.DISABLED, UserStatus.DELETED):
            raise ForbiddenError("sin autorización")
        if role not in (record.roles or []):
            raise ForbiddenError("sin autorización")
        return user

    return _dep
