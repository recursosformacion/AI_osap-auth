"""Rutas de recuperación de contraseña."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.dependencies import client_ip, client_user_agent, get_ctx
from api.schemas import PasswordResetConfirmRequest, PasswordResetRequestRequest
from application.context import AuthContext
from application.use_cases.password_reset import (
    ConfirmPasswordResetUseCase,
    RequestPasswordResetUseCase,
)

router = APIRouter(prefix="/auth/password-reset", tags=["password-reset"])


@router.post("/request", status_code=202)
async def request_reset(
    body: PasswordResetRequestRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    # Respuesta siempre genérica (anti-enumeración).
    await RequestPasswordResetUseCase(ctx).execute(email=body.email, ip=ip, user_agent=ua)
    return JSONResponse(
        {"message": "Si el email existe, recibirás un enlace de recuperación."},
        status_code=202,
    )


@router.post("/confirm", status_code=200)
async def confirm_reset(
    body: PasswordResetConfirmRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await ConfirmPasswordResetUseCase(ctx).execute(
        token=body.token, new_password=body.new_password, ip=ip, user_agent=ua
    )
    return JSONResponse({"message": "contraseña actualizada"})
