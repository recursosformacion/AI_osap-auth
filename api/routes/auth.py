"""Rutas de autenticación de usuario (register, login, sesiones, perfil)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.dependencies import (
    client_ip,
    client_user_agent,
    current_user,
    get_ctx,
    require_role,
)
from api.schemas import (
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ConfirmChangeEmailRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    SessionInfo,
    UserMeResponse,
    VerifyEmailRequest,
)
from application.context import AuthContext
from application.use_cases.admin_users import (
    AdminCreateUserUseCase,
    AdminDeleteUserUseCase,
    AdminGetUserUseCase,
    AdminListUsersUseCase,
    AdminUpdateUserUseCase,
)
from application.use_cases.delete_account import DeleteAccountUseCase
from application.use_cases.login import LoginUseCase
from application.use_cases.me import (
    ChangeEmailUseCase,
    ChangePasswordUseCase,
    ConfirmChangeEmailUseCase,
    GetMeUseCase,
)
from application.use_cases.refresh import RefreshUseCase
from application.use_cases.register import RegisterUseCase
from application.use_cases.sessions import (
    ListSessionsUseCase,
    LogoutAllUseCase,
    LogoutUseCase,
    RevokeSessionUseCase,
)
from application.use_cases.verify_email import (
    ResendVerificationUseCase,
    VerifyEmailUseCase,
)
from domain.exceptions import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> RegisterResponse:
    result = await RegisterUseCase(ctx).execute(
        email=body.email, password=body.password, name=body.name, ip=ip, user_agent=ua
    )
    # En producción el token se envía por email; en entornos no productivos se devuelve
    # para poder probar el flujo.
    include_token = ctx.settings.env != "production"
    return RegisterResponse(
        user_id=result.user_id,
        verification_token=result.verification_token if include_token else None,
        message="Si el email es nuevo, se ha enviado un enlace de verificación.",
    )


@router.post("/verify-email", status_code=200)
async def verify_email(
    body: VerifyEmailRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await VerifyEmailUseCase(ctx).execute(token=body.token, ip=ip, user_agent=ua)
    return JSONResponse({"message": "email verificado"})


@router.post("/resend-verification", status_code=200)
async def resend_verification(
    body: ResendVerificationRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await ResendVerificationUseCase(ctx).execute(email=body.email, ip=ip, user_agent=ua)
    return JSONResponse({"message": "si procede, se ha reenviado la verificación"})


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> LoginResponse:
    result = await LoginUseCase(ctx).execute(
        email=body.email,
        password=body.password,
        audience=body.audience,
        ip=ip,
        user_agent=ua,
    )
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        user_id=result.user_id,
        roles=result.roles,
        email_verified=result.email_verified,
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    body: RefreshRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> LoginResponse:
    result = await RefreshUseCase(ctx).execute(
        refresh_token=body.refresh_token,
        audience=body.audience,
        ip=ip,
        user_agent=ua,
    )
    claims = ctx.token_provider.verify_access_token(
        result.access_token,
        expected_audience=body.audience or ctx.settings.audience,
    )
    user = await ctx.users.get_by_id(uuid.UUID(claims["sub"]))
    if user is None:
        raise UnauthorizedError("usuario no encontrado")
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        user_id=str(user.id),
        roles=user.roles,
        email_verified=user.email_verified,
    )


@router.post("/logout", status_code=200)
async def logout(
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await LogoutUseCase(ctx).execute(
        session_id=uuid.UUID(user["jti"]),
        user_id=uuid.UUID(user["sub"]),
        ip=ip,
        user_agent=ua,
    )
    return JSONResponse({"message": "sesión cerrada"})


@router.post("/logout-all", status_code=200)
async def logout_all(
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await LogoutAllUseCase(ctx).execute(user_id=uuid.UUID(user["sub"]), ip=ip, user_agent=ua)
    return JSONResponse({"message": "todas las sesiones cerradas"})


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
) -> list[SessionInfo]:
    rows = await ListSessionsUseCase(ctx).execute(user_id=uuid.UUID(user["sub"]))
    return [SessionInfo(**row) for row in rows]


@router.delete("/sessions/{session_id}", status_code=200)
async def revoke_session(
    session_id: str,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await RevokeSessionUseCase(ctx).execute(
        session_id=uuid.UUID(session_id),
        user_id=uuid.UUID(user["sub"]),
        ip=ip,
        user_agent=ua,
    )
    return JSONResponse({"message": "sesión revocada"})


@router.get("/me", response_model=UserMeResponse)
async def me(
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
) -> UserMeResponse:
    return UserMeResponse(**await GetMeUseCase(ctx).execute(user_id=uuid.UUID(user["sub"])))


@router.post("/me/password", status_code=200)
async def change_password(
    body: ChangePasswordRequest,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await ChangePasswordUseCase(ctx).execute(
        user_id=uuid.UUID(user["sub"]),
        current_password=body.current_password,
        new_password=body.new_password,
        ip=ip,
        user_agent=ua,
    )
    return JSONResponse({"message": "contraseña actualizada"})


@router.post("/me/email", status_code=200)
async def change_email(
    body: ChangeEmailRequest,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await ChangeEmailUseCase(ctx).execute(
        user_id=uuid.UUID(user["sub"]), new_email=body.email, ip=ip, user_agent=ua
    )
    return JSONResponse({"message": "se ha solicitado el cambio de email"})


@router.post("/change-email/confirm", status_code=200)
async def confirm_change_email(
    body: ConfirmChangeEmailRequest,
    ctx: AuthContext = Depends(get_ctx),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await ConfirmChangeEmailUseCase(ctx).execute(token=body.token, ip=ip, user_agent=ua)
    return JSONResponse({"message": "cambio de email confirmado"})


@router.delete("/me", status_code=200)
async def delete_account(
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(current_user),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await DeleteAccountUseCase(ctx).execute(user_id=uuid.UUID(user["sub"]), ip=ip, user_agent=ua)
    return JSONResponse({"message": "cuenta eliminada"})


@router.get("/admin/users", response_model=list[UserMeResponse])
async def admin_list_users(
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(require_role("admin")),
) -> list[UserMeResponse]:
    return [UserMeResponse(**r) for r in await AdminListUsersUseCase(ctx).execute()]


@router.get("/admin/users/{user_id}", response_model=UserMeResponse)
async def admin_get_user(
    user_id: str,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(require_role("admin")),
) -> UserMeResponse:
    result = await AdminGetUserUseCase(ctx).execute(user_id=uuid.UUID(user_id))
    return UserMeResponse(**result)


@router.post("/admin/users", response_model=UserMeResponse, status_code=201)
async def admin_create_user(
    body: AdminCreateUserRequest,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(require_role("admin")),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> UserMeResponse:
    result = await AdminCreateUserUseCase(ctx).execute(
        email=body.email, password=body.password, name=body.name, roles=body.roles,
        actor=user["sub"], ip=ip, user_agent=ua,
    )
    return UserMeResponse(**result)


@router.patch("/admin/users/{user_id}", response_model=UserMeResponse)
async def admin_update_user(
    user_id: str,
    body: AdminUpdateUserRequest,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(require_role("admin")),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> UserMeResponse:
    result = await AdminUpdateUserUseCase(ctx).execute(
        user_id=uuid.UUID(user_id), name=body.name, roles=body.roles, status=body.status,
        actor=user["sub"], ip=ip, user_agent=ua,
    )
    return UserMeResponse(**result)


@router.delete("/admin/users/{user_id}", status_code=200)
async def admin_delete_user(
    user_id: str,
    ctx: AuthContext = Depends(get_ctx),
    user: dict = Depends(require_role("admin")),
    ip: str | None = Depends(client_ip),
    ua: str | None = Depends(client_user_agent),
) -> JSONResponse:
    await AdminDeleteUserUseCase(ctx).execute(
        user_id=uuid.UUID(user_id), actor=user["sub"], ip=ip, user_agent=ua
    )
    return JSONResponse({"message": "usuario eliminado"})
