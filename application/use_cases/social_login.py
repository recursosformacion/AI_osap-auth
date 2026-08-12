"""Casos de uso del login social (upstream): inicio y callback de proveedor externo."""

from __future__ import annotations

import base64
import hmac
import json
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime

from application.audit import audit
from application.context import AuthContext
from application.use_cases.oidc_authorize import (
    AuthorizationRequest,
    CompleteAuthorizationUseCase,
    ValidateAuthorizeRequestUseCase,
)
from domain.entities.provider_account import ProviderAccount
from domain.entities.user import User, UserStatus
from domain.exceptions import OAuthError
from domain.ports.social import SocialProvider
from domain.util import pkce_challenge

SOCIAL_STATE_TTL_SECONDS = 600


@dataclass
class SocialState:
    provider: str
    client_id: str | None
    redirect_uri: str | None
    scope: str
    response_type: str
    state: str | None
    nonce: str | None
    code_challenge: str | None
    code_challenge_method: str | None
    code_verifier: str
    exp: float


def encode_social_state(secret: str, payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), "sha256").hexdigest()
    return f"{body}.{sig}"


def decode_social_state(secret: str, token: str) -> SocialState | None:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), "sha256").hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        pad = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(pad).decode("utf-8"))
        if float(payload.get("exp", 0)) < time.time():
            return None
        return SocialState(
            provider=payload.get("provider", ""),
            client_id=payload.get("client_id"),
            redirect_uri=payload.get("redirect_uri"),
            scope=payload.get("scope", "openid profile"),
            response_type=payload.get("response_type", "code"),
            state=payload.get("state"),
            nonce=payload.get("nonce"),
            code_challenge=payload.get("code_challenge"),
            code_challenge_method=payload.get("code_challenge_method", "S256"),
            code_verifier=payload.get("code_verifier", ""),
            exp=float(payload.get("exp", 0)),
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


class SocialLoginStartUseCase:
    """Valida el contexto downstream (si lo hay) y devuelve la URL de authorize del proveedor."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, *, provider: str, params: dict[str, str]) -> str:
        social_provider = self._require_provider(provider)

        client_id = params.get("client_id")
        context: dict = {}
        if client_id:
            validated = await ValidateAuthorizeRequestUseCase(self._ctx).execute(params)
            context = {
                "client_id": validated.client_id,
                "redirect_uri": validated.redirect_uri,
                "scope": validated.scope,
                "response_type": validated.response_type,
                "state": validated.state,
                "nonce": validated.nonce,
                "code_challenge": validated.code_challenge,
                "code_challenge_method": validated.code_challenge_method,
            }

        verifier = self._ctx.secret_generator.generate(48)
        challenge = pkce_challenge(verifier)
        state_token = encode_social_state(
            self._ctx.settings.social_state_secret,
            {
                "provider": provider,
                "exp": time.time() + SOCIAL_STATE_TTL_SECONDS,
                "code_verifier": verifier,
                **context,
            },
        )
        redirect_uri = f"{self._ctx.settings.effective_issuer}/auth/oauth/{provider}/callback"
        return social_provider.authorize_url(redirect_uri, state_token, challenge)

    def _require_provider(self, provider: str) -> SocialProvider:
        social = self._ctx.social_providers.get(provider)
        if social is None:
            raise OAuthError("provider_not_enabled", f"proveedor {provider} no disponible")
        return social


@dataclass
class SocialCallbackResult:
    redirect_uri: str


class SocialLoginCallbackUseCase:
    """Canjea el code del proveedor, vincula/crea el usuario y completa el flujo downstream."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, provider: str, code: str, state_token: str, ip: str | None, user_agent: str | None
    ) -> SocialCallbackResult:
        social_provider = self._require_provider(provider)
        social_state = decode_social_state(self._ctx.settings.social_state_secret, state_token)
        if social_state is None or social_state.provider != provider:
            raise OAuthError("invalid_state", "estado social inválido")

        redirect_uri = f"{self._ctx.settings.effective_issuer}/auth/oauth/{provider}/callback"
        profile = await social_provider.exchange_and_profile(
            code, redirect_uri, social_state.code_verifier
        )
        user = await self._resolve_user(social_provider, profile, ip, user_agent)

        await audit(
            self._ctx,
            event_type="provider.link",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={"provider": provider},
        )

        if social_state.client_id and social_state.redirect_uri:
            request = AuthorizationRequest(
                client_id=social_state.client_id,
                redirect_uri=social_state.redirect_uri,
                scope=social_state.scope,
                response_type=social_state.response_type,
                state=social_state.state,
                nonce=social_state.nonce,
                code_challenge=social_state.code_challenge,
                code_challenge_method=social_state.code_challenge_method,
                login_url="",
            )
            result = await CompleteAuthorizationUseCase(self._ctx).execute(request, user.id)
            url = urllib.parse.urlparse(result.redirect_uri)
            query = urllib.parse.parse_qs(url.query)
            query["code"] = [result.code]
            if result.state:
                query["state"] = [result.state]
            parts = list(url)
            parts[4] = urllib.parse.urlencode(query, doseq=True)
            return SocialCallbackResult(redirect_uri=urllib.parse.urlunparse(parts))

        # Sin contexto downstream: solo se ha creado/vincado la cuenta.
        login_url = f"{self._ctx.settings.web_base_url.rstrip('/')}/auth/login"
        return SocialCallbackResult(redirect_uri=login_url)

    def _require_provider(self, provider: str) -> SocialProvider:
        social = self._ctx.social_providers.get(provider)
        if social is None:
            raise OAuthError("provider_not_enabled", f"proveedor {provider} no disponible")
        return social

    async def _resolve_user(
        self, provider: SocialProvider, profile, ip: str | None, user_agent: str | None
    ) -> User:
        account = await self._ctx.provider_accounts.get_by_provider_sub(provider.name, profile.sub)
        if account is not None:
            user = await self._ctx.users.get_by_id(account.user_id)
            if user is not None:
                return user

        email = profile.email
        if not email:
            raise OAuthError("invalid_profile", "el proveedor no devolvió un email")

        normalized = email.strip().lower()
        lookup = self._ctx.email_protector.lookup(normalized)
        user = await self._ctx.users.get_by_email_lookup(lookup)
        if user is None:
            cipher = self._ctx.email_protector.encrypt(normalized)
            user = User.new(
                email_lookup=lookup,
                email_cipher=cipher,
                password_hash="",  # sin contraseña: solo acceso social
                key_version=self._ctx.settings.key_version,
                name=profile.name,
            )
            if profile.email_verified:
                user.status = UserStatus.ACTIVE
                user.email_verified_at = datetime.now(UTC)
            user.touch()
            await self._ctx.users.save(user)
            await audit(
                self._ctx,
                event_type="register",
                actor=str(user.id),
                subject=str(user.id),
                ip=ip,
                user_agent=user_agent,
                outcome="success",
                context={"provider": provider.name, "verified": profile.email_verified},
            )

        new_account = ProviderAccount.new(
            provider=provider.name,
            provider_sub=profile.sub,
            user_id=user.id,
            email=normalized,
            name=profile.name,
        )
        await self._ctx.provider_accounts.save(new_account)
        return user
