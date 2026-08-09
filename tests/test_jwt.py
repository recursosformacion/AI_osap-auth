"""Tests de JWT/JWKS y emisión de tokens."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import uuid

import jwt
import pytest

from application.use_cases.service_tokens import IssueServiceTokenUseCase
from domain.entities.service_client import ServiceClient
from domain.exceptions import ServiceClientNotFoundError
from infrastructure.crypto.argon2_hasher import Argon2TokenHasher
from tests.fakes import make_context


def test_access_token_claims_no_pii() -> None:
    ctx, _ = make_context()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = ctx.token_provider.issue_access_token(
        user_id=user_id,
        session_id=session_id,
        roles=["user"],
        email_verified=True,
        scope="openid profile api:vote",
        ttl_seconds=900,
    )
    payload = jwt.decode(
        token,
        ctx.token_provider._keys.public_key,  # noqa: SLF001
        algorithms=["RS256"],
        audience="osap-api",
    )
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == str(session_id)
    assert payload["iss"] == "https://auth.osap"
    assert "email" not in payload
    assert "name" not in payload
    assert payload["email_verified"] is True
    assert payload["roles"] == ["user"]


def test_verify_access_token_rejects_pii_claim() -> None:
    ctx, _ = make_context()
    token = ctx.token_provider.issue_access_token(
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        roles=["user"],
        email_verified=True,
        scope="x",
        ttl_seconds=900,
    )
    # Un token manipulado con claim de email debe ser rechazado.
    header = jwt.get_unverified_header(token)
    payload = jwt.decode(
        token, ctx.token_provider._keys.public_key, algorithms=["RS256"],  # noqa: SLF001
        audience="osap-api",
    )
    payload["email"] = "leak@example.com"
    forged = jwt.encode(
        payload,
        ctx.token_provider._keys.private_key,
        algorithm="RS256",
        headers=header,  # noqa: SLF001
    )
    with pytest.raises(jwt.InvalidTokenError):
        ctx.token_provider.verify_access_token(forged, expected_audience="osap-api")


def test_jwks_public_only() -> None:
    ctx, _ = make_context()
    jwks = ctx.token_provider.jwks()
    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert key["alg"] == "RS256"
    assert "d" not in key  # sin exponente privado
    assert "p" not in key
    assert "q" not in key


def test_service_token_has_no_user_identity() -> None:
    ctx, _ = make_context()
    client = ServiceClient.new(
        client_secret_hash=Argon2TokenHasher().hash("s3cret"), scopes=["storage:read"]
    )
    token = ctx.token_provider.issue_service_token(
        client=client, scope="storage:read", ttl_seconds=300
    )
    payload = jwt.decode(
        token,
        ctx.token_provider._keys.public_key,
        algorithms=["RS256"],
        audience="osap-api",  # noqa: SLF001
    )
    assert payload["typ"] == "service"
    assert "roles" not in payload
    assert "email_verified" not in payload


async def test_service_token_issuance_scope_validation() -> None:
    ctx, _ = make_context()
    secret = "raw-secret-123"
    client = ServiceClient.new(
        client_secret_hash=ctx.token_hasher.hash(secret), scopes=["storage:read"]
    )
    await ctx.clients.save(client)
    result = await IssueServiceTokenUseCase(ctx).execute(
        client_id=str(client.client_id),
        client_secret=secret,
        requested_scope="storage:read",
        ip=None,
        user_agent=None,
    )
    assert result.scope == "storage:read"
    assert result.token_type == "Bearer"
    payload = jwt.decode(
        result.access_token,
        ctx.token_provider._keys.public_key,
        algorithms=["RS256"],  # noqa: SLF001
        audience="osap-api",
    )
    assert payload["typ"] == "service"


def test_user_token_has_token_use_user() -> None:
    ctx, _ = make_context()
    token = ctx.token_provider.issue_access_token(
        user_id=uuid.uuid4(), session_id=uuid.uuid4(), roles=["user"],
        email_verified=True, scope="openid profile", ttl_seconds=900,
    )
    payload = jwt.decode(
        token, ctx.token_provider._keys.public_key, algorithms=["RS256"],  # noqa: SLF001
        audience="osap-api",
    )
    assert payload["token_use"] == "user"


def test_service_token_has_token_use_service_and_no_user_identity() -> None:
    ctx, _ = make_context()
    client = ServiceClient.new(
        client_secret_hash=ctx.token_hasher.hash("s3cret"), scopes=["storage:read"]
    )
    token = ctx.token_provider.issue_service_token(
        client=client, scope="storage:read", ttl_seconds=300
    )
    payload = jwt.decode(
        token, ctx.token_provider._keys.public_key, algorithms=["RS256"],  # noqa: SLF001
        audience="osap-api",
    )
    assert payload["token_use"] == "service"
    assert payload["sub"] == str(client.client_id)
    assert "roles" not in payload
    assert "email_verified" not in payload


async def test_service_token_can_issue_storage_write_and_admin() -> None:
    ctx, _ = make_context()
    secret = "raw-secret-123"
    client = ServiceClient.new(
        client_secret_hash=ctx.token_hasher.hash(secret),
        scopes=["storage:write", "storage:admin"],
    )
    await ctx.clients.save(client)
    for scope in ("storage:write", "storage:admin"):
        result = await IssueServiceTokenUseCase(ctx).execute(
            client_id=str(client.client_id), client_secret=secret,
            requested_scope=scope, ip=None, user_agent=None,
        )
        assert result.scope == scope
        payload = jwt.decode(
            result.access_token, ctx.token_provider._keys.public_key,  # noqa: SLF001
            algorithms=["RS256"], audience="osap-api",
        )
        assert payload["scope"] == scope
        assert payload["token_use"] == "service"


async def test_client_without_scope_cannot_obtain_storage_write() -> None:
    ctx, _ = make_context()
    secret = "raw-secret-123"
    client = ServiceClient.new(
        client_secret_hash=ctx.token_hasher.hash(secret), scopes=["storage:read"]
    )
    await ctx.clients.save(client)
    with pytest.raises(ServiceClientNotFoundError):
        await IssueServiceTokenUseCase(ctx).execute(
            client_id=str(client.client_id), client_secret=secret,
            requested_scope="storage:write", ip=None, user_agent=None,
        )
