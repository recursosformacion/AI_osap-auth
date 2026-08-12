"""Casos de uso OIDC: validación de la petición de authorize y emisión del code."""

from __future__ import annotations

import urllib.parse
import uuid
from dataclasses import dataclass

from application.audit import audit
from application.context import AuthContext
from domain.entities.authorization_code import AuthorizationCode
from domain.entities.oauth_client import OAuthClient
from domain.exceptions import OAuthClientNotFoundError, OAuthError


@dataclass
class AuthorizationRequest:
    client_id: str
    redirect_uri: str
    scope: str
    response_type: str
    state: str | None
    nonce: str | None
    code_challenge: str | None
    code_challenge_method: str | None
    login_url: str


class ValidateAuthorizeRequestUseCase:
    """Valida la petición de authorize contra el RP y prepara la URL de login embebida."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(self, params: dict[str, str]) -> AuthorizationRequest:
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        response_type = params.get("response_type", "")
        scope = params.get("scope", "")
        state = params.get("state")
        nonce = params.get("nonce")
        code_challenge = params.get("code_challenge")
        code_challenge_method = params.get("code_challenge_method") or "S256"

        if client_id == "" or redirect_uri == "":
            raise OAuthClientNotFoundError("invalid_request", error="invalid_request")
        client = await self._ctx.oauth_clients.get_by_id(client_id)
        if client is None or not client.enabled:
            raise OAuthClientNotFoundError("invalid_client", error="invalid_client")
        if not client.allows_redirect_uri(redirect_uri):
            raise OAuthClientNotFoundError(
                "invalid_request: redirect_uri no registrada", error="invalid_request"
            )

        if response_type != "code" or not client.allows_response_type(response_type):
            raise OAuthError(
                "unsupported_response_type",
                "solo se soporta code",
                redirect_uri=redirect_uri,
                state=state,
            )
        if not client.allows_scope(scope):
            raise OAuthError(
                "invalid_scope", "scope no permitido", redirect_uri=redirect_uri, state=state
            )
        if client.pkce_required and not code_challenge:
            raise OAuthError(
                "invalid_request",
                "code_challenge (PKCE S256) requerido",
                redirect_uri=redirect_uri,
                state=state,
            )
        if code_challenge and code_challenge_method not in ("S256",):
            raise OAuthError(
                "invalid_request",
                "code_challenge_method debe ser S256",
                redirect_uri=redirect_uri,
                state=state,
            )

        return AuthorizationRequest(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            response_type=response_type,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            login_url=self._build_login_url(
                client, redirect_uri, scope, state, nonce, code_challenge, code_challenge_method
            ),
        )

    def _build_login_url(
        self,
        client: OAuthClient,
        redirect_uri: str,
        scope: str,
        state: str | None,
        nonce: str | None,
        code_challenge: str | None,
        code_challenge_method: str | None,
    ) -> str:
        query = {
            "client_id": client.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "embed": "1",
        }
        if state:
            query["state"] = state
        if nonce:
            query["nonce"] = nonce
        if code_challenge:
            query["code_challenge"] = code_challenge
        if code_challenge_method:
            query["code_challenge_method"] = code_challenge_method
        base = self._ctx.settings.web_base_url.rstrip("/")
        return f"{base}/auth/login?{urllib.parse.urlencode(query)}"


@dataclass
class CompleteAuthorizationResult:
    redirect_uri: str
    code: str
    state: str | None


class CompleteAuthorizationUseCase:
    """Emite un Authorization Code de un solo uso para un usuario autenticado."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, request: AuthorizationRequest, user_id: uuid.UUID
    ) -> CompleteAuthorizationResult:
        raw_code = self._ctx.secret_generator.generate(32)
        code = AuthorizationCode.new(
            client_id=request.client_id,
            user_id=user_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            code_hash=self._ctx.token_hasher.hash(raw_code),
            ttl_seconds=self._ctx.settings.authorization_code_ttl_seconds,
            code_challenge=request.code_challenge,
            code_challenge_method=request.code_challenge_method,
            nonce=request.nonce,
        )
        await self._ctx.authorization_codes.save(code)
        await audit(
            self._ctx,
            event_type="oauth.authorize",
            actor=str(user_id),
            subject=str(user_id),
            ip=None,
            user_agent=None,
            outcome="success",
            context={"client": str(request.client_id)},
        )
        return CompleteAuthorizationResult(
            redirect_uri=request.redirect_uri,
            code=raw_code,
            state=request.state,
        )
