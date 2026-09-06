"""Emisión/validación de access tokens (usuario) y service tokens (máquina a máquina)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from domain.entities.service_client import ServiceClient
from domain.ports.jwt import TokenProvider
from infrastructure.jwt.jwks import jwk_from_public_key

TOKEN_TYPES = ("access", "service")

# Claims que NO deben aparecer nunca en un access token (PII o secretos).
_FORBIDDEN_ACCESS_CLAIMS = ("email", "email_lookup", "email_cipher", "name", "sub_id", "password")


class PyJwtTokenProvider(TokenProvider):
    def __init__(
        self,
        *,
        private_key_pem: str,
        public_key_pem: str,
        kid: str,
        issuer: str,
        audience: str,
        clock_skew_seconds: int = 30,
    ) -> None:
        from infrastructure.jwt.keys import RsaKeys

        self._keys = RsaKeys(private_key_pem=private_key_pem, public_key_pem=public_key_pem)
        self._kid = kid
        self._issuer = issuer
        self._audience = audience
        self._clock_skew = clock_skew_seconds

    def issue_access_token(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        roles: list[str],
        email_verified: bool,
        scope: str,
        ttl_seconds: int,
        audience: str | None = None,
        nonce: str | None = None,
        issuer: str | None = None,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "iss": issuer or self._issuer,
            "sub": str(user_id),
            "aud": audience or self._audience,
            "jti": str(session_id),
            "roles": roles,
            "email_verified": email_verified,
            "scope": scope,
            "typ": "access",
            "token_use": "user",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        }
        if nonce:
            payload["nonce"] = nonce
        return self._encode(payload)

    def issue_service_token(
        self,
        *,
        client: ServiceClient,
        scope: str,
        ttl_seconds: int,
        audience: str | None = None,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "iss": self._issuer,
            "sub": str(client.client_id),
            "aud": audience or self._audience,
            "jti": str(uuid.uuid4()),
            "scope": scope,
            "typ": "service",
            "token_use": "service",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        }
        return self._encode(payload)

    def verify_access_token(self, token: str, *, expected_audience: str) -> dict[str, Any]:
        payload = self._decode(token, expected_audience)
        # token_use es el discriminador canónico; `typ` se mantiene por retrocompatibilidad.
        if payload.get("typ") != "access" and payload.get("token_use") != "user":
            raise jwt.InvalidTokenError("token no es de acceso")
        if any(claim in payload for claim in _FORBIDDEN_ACCESS_CLAIMS):
            raise jwt.InvalidTokenError("token contiene PII prohibida")
        return payload

    def verify_service_token(self, token: str, *, expected_audience: str) -> dict[str, Any]:
        payload = self._decode(token, expected_audience)
        if payload.get("typ") != "service" and payload.get("token_use") != "service":
            raise jwt.InvalidTokenError("token no es de servicio")
        return payload

    def jwks(self) -> dict[str, Any]:
        return {"keys": [jwk_from_public_key(self._keys.public_key, self._kid)]}

    def _encode(self, payload: dict[str, Any]) -> str:
        return jwt.encode(
            payload, self._keys.private_key, algorithm="RS256", headers={"kid": self._kid}
        )

    def _decode(self, token: str, expected_audience: str) -> dict[str, Any]:
        return jwt.decode(
            token,
            self._keys.public_key,
            algorithms=["RS256"],
            issuer=self._issuer,
            audience=expected_audience,
            leeway=self._clock_skew,
            options={"require": ["iss", "sub", "aud", "exp", "iat", "jti"]},
        )


def build_jwks(public_key_pem: str, kid: str) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization

    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    return {"keys": [jwk_from_public_key(public_key, kid)]}
