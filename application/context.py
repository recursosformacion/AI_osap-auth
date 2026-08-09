"""Contexto de aplicación: agrupa puertos y configuración para los casos de uso."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.ports.audit_repository import AuditRepository
from domain.ports.crypto import (
    EmailProtector,
    PasswordHasher,
    SecretGenerator,
    TokenHasher,
)
from domain.ports.event_bus import EventPublisher
from domain.ports.jwt import TokenProvider
from domain.ports.rate_limiter import RateLimiter
from domain.ports.service_client_repository import ServiceClientRepository
from domain.ports.session_repository import SessionRepository
from domain.ports.token_repository import TokenRepository
from domain.ports.user_repository import UserRepository


@dataclass
class AuthSettingsView:
    """Valores de configuración relevantes para los casos de uso (sin secretos)."""

    issuer: str
    audience: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    verification_token_ttl_hours: float
    password_reset_token_ttl_hours: float
    key_version: int
    env: str
    register_per_minute: int
    login_per_minute: int
    resend_verification_per_minute: int
    password_reset_request_per_minute: int
    password_reset_confirm_per_minute: int


@dataclass
class AuthContext:
    """Dependencias compartidas por todos los casos de uso."""

    users: UserRepository
    sessions: SessionRepository
    tokens: TokenRepository
    clients: ServiceClientRepository
    audit: AuditRepository
    rate_limiter: RateLimiter
    password_hasher: PasswordHasher
    token_hasher: TokenHasher
    secret_generator: SecretGenerator
    email_protector: EmailProtector
    token_provider: TokenProvider
    events: EventPublisher
    settings: AuthSettingsView

    _audit_chain: str = field(default="", init=False)

    async def begin_audit_chain(self) -> None:
        self._audit_chain = await self.audit.last_hash()

    @property
    def audit_chain(self) -> str:
        return self._audit_chain

    def set_audit_chain(self, value: str) -> None:
        self._audit_chain = value
