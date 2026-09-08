"""Fakes de repositorios y construcción de contexto para tests de osap-auth."""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from application.context import AuthContext, AuthSettingsView
from domain.entities.audit_event import AuditEvent
from domain.entities.authorization_code import AuthorizationCode
from domain.entities.oauth_client import OAuthClient
from domain.entities.provider_account import ProviderAccount
from domain.entities.service_client import ServiceClient
from domain.entities.session import Session
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.entities.user import User
from domain.ports.audit_repository import AuditRepository
from domain.ports.authorization_code_repository import AuthorizationCodeRepository
from domain.ports.oauth_client_repository import OAuthClientRepository
from domain.ports.provider_account_repository import ProviderAccountRepository
from domain.ports.service_client_repository import ServiceClientRepository
from domain.ports.session_repository import SessionRepository
from domain.ports.token_repository import TokenRepository
from domain.ports.user_repository import UserRepository
from infrastructure.crypto.aes_gcm import AesGcmEmailProtector
from infrastructure.crypto.argon2_hasher import Argon2PasswordHasher
from infrastructure.crypto.hmac_hasher import HmacTokenHasher
from infrastructure.crypto.secrets import SecretGenerator
from infrastructure.events.event_bus import LoggingEventPublisher
from infrastructure.jwt.tokens import PyJwtTokenProvider
from infrastructure.rate_limiting.memory_rate_limiter import MemoryRateLimiter


def make_rsa_keys() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(str(user_id))

    async def get_by_email_lookup(self, email_lookup: str) -> User | None:
        for u in self._users.values():
            if u.email_lookup == email_lookup:
                return u
        return None

    async def exists(self, email_lookup: str) -> bool:
        return await self.get_by_email_lookup(email_lookup) is not None

    async def list_all(self) -> list[User]:
        return list(self._users.values())

    async def save(self, user: User) -> None:
        self._users[str(user.id)] = user


class FakeSessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        return self._sessions.get(str(session_id))

    async def get_by_refresh_hash(self, refresh_token_hash: str) -> Session | None:
        for s in self._sessions.values():
            if s.refresh_token_hash == refresh_token_hash:
                return s
        return None

    async def get_by_previous_refresh_hash(
        self, previous_refresh_token_hash: str
    ) -> Session | None:
        for s in self._sessions.values():
            if s.previous_refresh_token_hash == previous_refresh_token_hash:
                return s
        return None

    async def list_for_user(self, user_id: uuid.UUID) -> list[Session]:
        return [s for s in self._sessions.values() if s.user_id == user_id]

    async def save(self, session: Session) -> None:
        self._sessions[str(session.id)] = session

    async def revoke(self, session_id: uuid.UUID) -> None:
        s = self._sessions.get(str(session_id))
        if s is not None:
            s.revoke()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        for s in self._sessions.values():
            if s.user_id == user_id:
                s.revoke()


class FakeTokenRepository(TokenRepository):
    def __init__(self) -> None:
        self._tokens: list[TokenRecord] = []

    async def get_by_hash(self, token_hash: str, purpose: TokenPurpose) -> TokenRecord | None:
        for t in self._tokens:
            if t.token_hash == token_hash and t.purpose == purpose:
                return t
        return None

    async def save(self, token: TokenRecord) -> None:
        self._tokens.append(token)

    async def mark_used(self, token_id: uuid.UUID) -> None:
        for t in self._tokens:
            if t.id == token_id:
                t.mark_used()


class FakeServiceClientRepository(ServiceClientRepository):
    def __init__(self) -> None:
        self._clients: dict[str, ServiceClient] = {}

    async def get_by_id(self, client_id: uuid.UUID) -> ServiceClient | None:
        return self._clients.get(str(client_id))

    async def save(self, client: ServiceClient) -> None:
        self._clients[str(client.client_id)] = client


class FakeOAuthClientRepository(OAuthClientRepository):
    def __init__(self) -> None:
        self._clients: dict[str, OAuthClient] = {}

    async def get_by_id(self, client_id: str) -> OAuthClient | None:
        return self._clients.get(client_id)

    async def save(self, client: OAuthClient) -> None:
        self._clients[str(client.client_id)] = client


class FakeAuthorizationCodeRepository(AuthorizationCodeRepository):
    def __init__(self) -> None:
        self._codes: dict[str, AuthorizationCode] = {}

    async def get_by_hash(self, code_hash: str) -> AuthorizationCode | None:
        return self._codes.get(code_hash)

    async def save(self, code: AuthorizationCode) -> None:
        self._codes[code.code_hash] = code

    async def mark_used(self, code_id: uuid.UUID) -> None:
        for c in self._codes.values():
            if c.id == code_id:
                c.mark_used()


class FakeProviderAccountRepository(ProviderAccountRepository):
    def __init__(self) -> None:
        self._accounts: dict[tuple[str, str], ProviderAccount] = {}

    async def get_by_provider_sub(self, provider: str, provider_sub: str) -> ProviderAccount | None:
        return self._accounts.get((provider, provider_sub))

    async def save(self, account: ProviderAccount) -> None:
        self._accounts[(account.provider, account.provider_sub)] = account


class FakeAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    async def last_hash(self) -> str:
        return self._events[-1].hash if self._events else ""

    async def purge_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        before = len(self._events)
        self._events = [e for e in self._events if (e.timestamp or datetime.min) >= cutoff]
        return before - len(self._events)

    @property
    def events(self) -> list[AuditEvent]:
        return self._events


def make_settings_view() -> AuthSettingsView:
    return AuthSettingsView(
        issuer="https://auth.osap",
        audience="osap-api",
        allowed_token_audiences=["osap-api"],
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=2_592_000,
        verification_token_ttl_hours=24,
        password_reset_token_ttl_hours=1,
        key_version=1,
        env="test",
        register_per_minute=1000,
        login_per_minute=1000,
        resend_verification_per_minute=1000,
        password_reset_request_per_minute=1000,
        password_reset_confirm_per_minute=1000,
        public_base_url="https://auth.osap",
        public_path_prefix="",
        web_base_url="http://osap-auth",
        authorization_code_ttl_seconds=300,
        social_state_secret="test-social-state-secret",
        social_providers_enabled={},
    )


def make_context(
    *,
    users: FakeUserRepository | None = None,
    sessions: FakeSessionRepository | None = None,
    tokens: FakeTokenRepository | None = None,
    clients: FakeServiceClientRepository | None = None,
    oauth_clients: FakeOAuthClientRepository | None = None,
    authorization_codes: FakeAuthorizationCodeRepository | None = None,
    provider_accounts: FakeProviderAccountRepository | None = None,
    audit: FakeAuditRepository | None = None,
    social_providers: dict[str, object] | None = None,
) -> tuple[AuthContext, list[object]]:
    private_pem, public_pem = make_rsa_keys()
    provider = PyJwtTokenProvider(
        private_key_pem=private_pem,
        public_key_pem=public_pem,
        kid="test-key",
        issuer="https://auth.osap",
        audience="osap-api",
    )
    protector = AesGcmEmailProtector(
        aead_key_b64=base64.urlsafe_b64encode(b"0" * 32).decode(),
        pepper="test-pepper",
    )
    ctx = AuthContext(
        users=users or FakeUserRepository(),
        sessions=sessions or FakeSessionRepository(),
        tokens=tokens or FakeTokenRepository(),
        clients=clients or FakeServiceClientRepository(),
        oauth_clients=oauth_clients or FakeOAuthClientRepository(),
        authorization_codes=authorization_codes or FakeAuthorizationCodeRepository(),
        provider_accounts=provider_accounts or FakeProviderAccountRepository(),
        audit=audit or FakeAuditRepository(),
        rate_limiter=MemoryRateLimiter(),
        password_hasher=Argon2PasswordHasher(),
        token_hasher=HmacTokenHasher(pepper="test-pepper"),
        secret_generator=SecretGenerator(),
        email_protector=protector,
        token_provider=provider,
        events=LoggingEventPublisher(),
        settings=make_settings_view(),
        social_providers=social_providers or {},  # type: ignore[arg-type]
    )
    return ctx, [provider, protector, ctx.events]
