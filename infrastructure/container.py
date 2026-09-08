"""Contenedor de dependencias de osap-auth (composición del contexto)."""

from __future__ import annotations

import aiomysql

from application.context import AuthContext, AuthSettingsView
from domain.ports.social import SocialProvider
from infrastructure.config import Settings
from infrastructure.crypto.aes_gcm import AesGcmEmailProtector
from infrastructure.crypto.argon2_hasher import Argon2PasswordHasher
from infrastructure.crypto.hmac_hasher import HmacTokenHasher
from infrastructure.crypto.secrets import SecretGenerator
from infrastructure.events.event_bus import LoggingEventPublisher
from infrastructure.jwt.tokens import PyJwtTokenProvider
from infrastructure.rate_limiting.memory_rate_limiter import MemoryRateLimiter
from infrastructure.repositories.sql_audit_repository import SqlAuditRepository
from infrastructure.repositories.sql_authorization_code_repository import (
    SqlAuthorizationCodeRepository,
)
from infrastructure.repositories.sql_oauth_client_repository import (
    SqlOAuthClientRepository,
)
from infrastructure.repositories.sql_provider_account_repository import (
    SqlProviderAccountRepository,
)
from infrastructure.repositories.sql_service_client_repository import (
    SqlServiceClientRepository,
)
from infrastructure.repositories.sql_session_repository import SqlSessionRepository
from infrastructure.repositories.sql_token_repository import SqlTokenRepository
from infrastructure.repositories.sql_user_repository import SqlUserRepository
from infrastructure.social.providers import GitHubProvider, GoogleProvider


def build_settings_view(settings: Settings) -> AuthSettingsView:
    return AuthSettingsView(
        issuer=settings.issuer,
        audience=settings.audience,
        allowed_token_audiences=settings.allowed_token_audiences,
        access_token_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
        verification_token_ttl_hours=settings.verification_token_ttl_hours,
        password_reset_token_ttl_hours=settings.password_reset_token_ttl_hours,
        key_version=settings.key_version,
        env=settings.env,
        register_per_minute=settings.rate_limit.register_per_minute,
        login_per_minute=settings.rate_limit.login_per_minute,
        resend_verification_per_minute=settings.rate_limit.resend_verification_per_minute,
        password_reset_request_per_minute=settings.rate_limit.password_reset_request_per_minute,
        password_reset_confirm_per_minute=settings.rate_limit.password_reset_confirm_per_minute,
        public_base_url=settings.public_base_url,
        public_path_prefix=settings.public_path_prefix,
        web_base_url=settings.web_base_url,
        authorization_code_ttl_seconds=settings.authorization_code_ttl_seconds,
        social_state_secret=settings.social_state_secret,
        social_providers_enabled=settings.social_enabled,
    )


def build_context(settings: Settings, pool: aiomysql.Pool) -> AuthContext:
    email_protector = AesGcmEmailProtector(
        aead_key_b64=settings.crypto.email_aead_key_b64,
        pepper=settings.crypto.email_hmac_pepper,
    )
    token_provider = PyJwtTokenProvider(
        private_key_pem=settings.crypto.jwt_private_key,
        public_key_pem=settings.crypto.jwt_public_key,
        kid=settings.crypto.jwt_kid,
        issuer=settings.issuer,
        audience=settings.audience,
    )
    social_providers: dict[str, SocialProvider] = {}
    for name, creds in settings.social_credentials.items():
        if name == "google":
            social_providers[name] = GoogleProvider(
                client_id=creds["client_id"], client_secret=creds["client_secret"]
            )
        elif name == "github":
            social_providers[name] = GitHubProvider(
                client_id=creds["client_id"], client_secret=creds["client_secret"]
            )
    return AuthContext(
        users=SqlUserRepository(pool),
        sessions=SqlSessionRepository(pool),
        tokens=SqlTokenRepository(pool),
        clients=SqlServiceClientRepository(pool),
        oauth_clients=SqlOAuthClientRepository(pool),
        authorization_codes=SqlAuthorizationCodeRepository(pool),
        provider_accounts=SqlProviderAccountRepository(pool),
        audit=SqlAuditRepository(pool),
        rate_limiter=MemoryRateLimiter(),
        password_hasher=Argon2PasswordHasher(),
        token_hasher=HmacTokenHasher(
            pepper=settings.crypto.token_hmac_pepper or settings.crypto.email_hmac_pepper
        ),
        secret_generator=SecretGenerator(),
        email_protector=email_protector,
        token_provider=token_provider,
        events=LoggingEventPublisher(),
        settings=build_settings_view(settings),
        social_providers=social_providers,
    )
