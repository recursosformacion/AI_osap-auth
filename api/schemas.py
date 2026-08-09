"""Schemas de petición/respuesta de la API de osap-auth."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class PasswordResetRequestRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ChangeEmailRequest(BaseModel):
    email: str


class ConfirmChangeEmailRequest(BaseModel):
    token: str


class OAuthTokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str
    scope: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    scope: str = ""


class RegisterResponse(BaseModel):
    user_id: str | None = None
    verification_token: str | None = None
    message: str


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    name: str | None = None
    roles: list[str]
    email_verified: bool
    status: str
    created_at: str | None = None


class SessionInfo(BaseModel):
    id: str
    created_at: str
    last_used_at: str
    revoked: bool
    ip: str | None = None
    user_agent: str | None = None
    device_label: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    roles: list[str]
    email_verified: bool


class VersionResponse(BaseModel):
    contract: str
    version: str


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str | None = Field(default=None, max_length=120)
    roles: list[str] = Field(default_factory=lambda: ["user"])


class AdminUpdateUserRequest(BaseModel):
    name: str | None = None
    roles: list[str] | None = None
    status: str | None = None
