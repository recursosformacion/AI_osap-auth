"""Tests del contrato de audiencia (4D-1): emisión por cliente + allowlist.

Cubren la emisión/verificación de service tokens:
- audiencia permitida (allowlist del client) → token con aud=osap-support;
- audiencia NO permitida → rechazada (400);
- sin audiencia → comportamiento actual (audiencia global por defecto).
Los casos "scope sin audiencia / audiencia sin scope no son suficientes" se verifican en
el lado consumidor (osap-support ServiceAuthenticator), no en la emisión.
"""

from __future__ import annotations

import asyncio
from typing import Any

import jwt
from fastapi.testclient import TestClient

from application.use_cases.service_clients import CreateServiceClientUseCase


def _run(awaitable) -> Any:
    return asyncio.run(awaitable)


def _create_client(
    ctx, allowed_audiences: list[str] | None = None
) -> tuple[str, str]:
    result = _run(
        CreateServiceClientUseCase(ctx).execute(
            scopes=["storage:read"], allowed_audiences=allowed_audiences
        )
    )
    return result.client_id, result.client_secret


def _issue(app: TestClient, client_id: str, secret: str, audience: str | None) -> Any:
    body: dict[str, Any] = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": secret,
        "scope": "storage:read",
    }
    if audience is not None:
        body["audience"] = audience
    return app.post("/oauth/token", json=body)


def test_service_token_allowed_audience_osap_support(ctx) -> None:
    from api.main import create_app

    client_id, secret = _create_client(ctx, allowed_audiences=["osap-support"])
    app = TestClient(create_app(ctx))
    r = _issue(app, client_id, secret, audience="osap-support")
    assert r.status_code == 200
    token = r.json()["access_token"]

    claims = ctx.token_provider.verify_service_token(
        token, expected_audience="osap-support"
    )
    assert claims["aud"] == "osap-support"
    assert claims["token_use"] == "service"

    # La misma audiencia estricta NO sirve para el default del ecosistema.
    try:
        ctx.token_provider.verify_service_token(token, expected_audience="osap-api")
        raise AssertionError("token con aud=osap-support no debe validar con aud=osap-api")
    except jwt.InvalidTokenError:
        pass


def test_service_token_audience_not_allowed_rejected(ctx) -> None:
    from api.main import create_app

    client_id, secret = _create_client(ctx, allowed_audiences=["osap-support"])
    app = TestClient(create_app(ctx))
    r = _issue(app, client_id, secret, audience="osap-storage")
    assert r.status_code == 401


def test_service_token_audience_rejected_without_allowlist(ctx) -> None:
    from api.main import create_app

    client_id, secret = _create_client(ctx, allowed_audiences=None)
    app = TestClient(create_app(ctx))
    r = _issue(app, client_id, secret, audience="osap-support")
    assert r.status_code == 401


def test_service_token_without_audience_keeps_default(ctx) -> None:
    from api.main import create_app

    client_id, secret = _create_client(ctx, allowed_audiences=None)
    app = TestClient(create_app(ctx))
    r = _issue(app, client_id, secret, audience=None)
    assert r.status_code == 200
    token = r.json()["access_token"]
    claims = ctx.token_provider.verify_service_token(
        token, expected_audience=ctx.settings.audience
    )
    assert claims["aud"] == ctx.settings.audience
