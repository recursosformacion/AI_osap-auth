"""Schemas de petición/respuesta de la API de osap-auth."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str
    audience: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
    audience: str | None = None


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


class UpdateMeRequest(BaseModel):
    """Nombre y nickname del propio usuario (el de OIDC/Google es solo el valor inicial)."""

    name: str = Field(min_length=1, max_length=100)
    nickname: str | None = Field(default=None, min_length=3, max_length=30)


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


class PublicNameItem(BaseModel):
    """Item del lookup M2M de identidad pública.

    Expone `id`, `name`, `nickname` y `nickname_public_consent` (autorización de cuenta para
    mostrarse públicamente). Sigue sin email ni roles.
    """

    id: str
    name: str | None = None
    nickname: str | None = None
    nickname_public_consent: bool = False


class PublicUserItem(BaseModel):
    """Entrada de la lista pública de colaboradores: `id` + `nickname` (sin name/email/roles)."""

    id: str
    nickname: str


class OnboardingState(BaseModel):
    """Estado de onboarding derivado de los datos reales (fuente de verdad: Auth)."""

    required: bool
    completed_at: str | None = None
    terms_accepted: bool
    privacy_accepted: bool
    nickname_set: bool
    terms_version_current: str
    privacy_version_current: str


class MembershipInfo(BaseModel):
    """Pertenencia del usuario a una entidad, con su estado de aprobación."""

    id: str
    entity_id: str
    entity_name: str
    entity_kind: str
    entity_email: str | None = None
    status: str
    is_representative: bool
    requested_at: str
    decided_at: str | None = None


class EntityListItem(BaseModel):
    """Entidad dada de alta, ofrecida en el alta y en la ficha del usuario."""

    id: str
    name: str
    kind: str


class EntityRequestInfo(BaseModel):
    """Solicitud de incorporación pendiente, para el gestor de la entidad."""

    id: str
    entity_id: str
    entity_name: str
    entity_kind: str
    user_id: str
    nickname: str | None = None
    name: str | None = None
    requested_at: str


class DecideEntityRequest(BaseModel):
    """Decisión del gestor sobre una solicitud de incorporación."""

    action: Literal["approve", "reject"]


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    name: str | None = None
    nickname: str | None = None
    phone: str | None = None
    roles: list[str]
    email_verified: bool
    status: str
    created_at: str | None = None
    onboarding: OnboardingState | None = None
    nickname_public_consent: bool = False
    memberships: list[MembershipInfo] = Field(default_factory=list)


class OnboardingRequest(BaseModel):
    """Completa el onboarding: handle único + aceptación de las versiones legales vigentes.

    Opcionalmente, el usuario indica si representa una entidad (nombre + tipo) o si
    pertenece a una entidad ya registrada (`entity_id`).
    """

    nickname: str = Field(min_length=3, max_length=30)
    terms_version: str
    privacy_version: str
    entity_id: str | None = None
    entity_name: str | None = Field(default=None, max_length=120)
    entity_kind: str | None = Field(default=None, max_length=32)
    entity_email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)


class UpdatePhoneRequest(BaseModel):
    """Teléfono voluntario para comunicaciones por WhatsApp (`null` o vacío lo borra)."""

    phone: str | None = Field(default=None, max_length=32)


class UpdateMyEntityRequest(BaseModel):
    """Cambio de entidad desde la ficha del usuario.

    - `join`: solicitar pertenecer a `entity_id` (queda pendiente de aprobación).
    - `leave`: dejar de pertenecer a `entity_id`.
    - `represent`: crear una entidad (`entity_name` + `entity_kind`) o actualizar una
      que ya gestiona (`entity_id` + nombre/tipo).
    """

    action: Literal["join", "leave", "represent"]
    entity_id: str | None = None
    entity_name: str | None = Field(default=None, max_length=120)
    entity_kind: str | None = Field(default=None, max_length=32)
    entity_email: str | None = Field(default=None, max_length=254)


class LegalCurrentResponse(BaseModel):
    terms_version: str
    privacy_version: str
    terms_url: str
    privacy_url: str


class PublicConsentRequest(BaseModel):
    """Autorización de cuenta para publicar el nickname."""

    value: bool


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
    nickname: str | None = None
    phone: str | None = None
    roles: list[str] | None = None
    status: str | None = None


class NotifyRecognitionRequest(BaseModel):
    recognition_type: str
    action: str = "granted"
    project: str = "omr"
