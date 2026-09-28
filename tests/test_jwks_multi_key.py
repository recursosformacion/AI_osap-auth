"""SEC-A (paso 1): JWKS multi-clave por `kid` en osap-auth, sin cambiar el kid que firma.

Publica y verifica el conjunto de claves (activa + anteriores) para preparar una rotación
con solape reversible.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import jwt
import pytest

from infrastructure.jwt.tokens import PyJwtTokenProvider
from tests.fakes import make_rsa_keys

_ISS = "https://auth.osap"
_AUD = "osap-api"
_OLD_KID = "osap-auth-v1"
_NEW_KID = "osap-auth-v2"


def _payload(exp_offset: int = 300) -> dict[str, Any]:
    now = int(time.time())
    return {
        "iss": _ISS,
        "sub": str(uuid.uuid4()),
        "aud": _AUD,
        "jti": str(uuid.uuid4()),
        "roles": ["user"],
        "email_verified": True,
        "scope": "openid profile",
        "typ": "access",
        "token_use": "user",
        "iat": now,
        "exp": now + exp_offset,
    }


def _provider_with_ring() -> tuple[PyJwtTokenProvider, str, str]:
    old_private, old_public = make_rsa_keys()
    new_private, new_public = make_rsa_keys()
    provider = PyJwtTokenProvider(
        private_key_pem=old_private,
        public_key_pem=old_public,
        kid=_OLD_KID,
        issuer=_ISS,
        audience=_AUD,
        previous_public_keys={_NEW_KID: new_public},
    )
    return provider, old_private, new_private


def test_jwks_contiene_ambas_claves() -> None:
    provider, _, _ = _provider_with_ring()
    kids = {key["kid"] for key in provider.jwks()["keys"]}
    assert kids == {_OLD_KID, _NEW_KID}


def test_token_firmado_con_clave_antigua_valido_y_kid_sin_cambiar() -> None:
    provider, _, _ = _provider_with_ring()
    token = provider.issue_access_token(
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        roles=["user"],
        email_verified=True,
        scope="openid profile",
        ttl_seconds=300,
    )
    assert jwt.get_unverified_header(token)["kid"] == _OLD_KID
    payload = provider.verify_access_token(token, expected_audience=_AUD)
    assert payload["aud"] == _AUD


def test_token_firmado_con_clave_nueva_valido() -> None:
    provider, _, new_private = _provider_with_ring()
    token = jwt.encode(
        _payload(), new_private, algorithm="RS256", headers={"kid": _NEW_KID}
    )
    payload = provider.verify_access_token(token, expected_audience=_AUD)
    assert payload["token_use"] == "user"


def test_kid_desconocido_rechazado() -> None:
    provider, _, new_private = _provider_with_ring()
    token = jwt.encode(
        _payload(), new_private, algorithm="RS256", headers={"kid": "ghost"}
    )
    with pytest.raises(jwt.InvalidTokenError):
        provider.verify_access_token(token, expected_audience=_AUD)


def test_firma_no_corresponde_al_kid_rechazada() -> None:
    provider, _, new_private = _provider_with_ring()
    # Firmado con la clave nueva pero anunciando el kid antiguo.
    token = jwt.encode(
        _payload(), new_private, algorithm="RS256", headers={"kid": _OLD_KID}
    )
    with pytest.raises(jwt.InvalidTokenError):
        provider.verify_access_token(token, expected_audience=_AUD)
