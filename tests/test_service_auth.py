"""Tests de service-to-service auth (client_credentials) vía API."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi.testclient import TestClient

from application.use_cases.service_clients import CreateServiceClientUseCase


def _run(awaitable) -> Any:
    return asyncio.run(awaitable)


def _create_client(ctx) -> tuple[str, str]:
    result = _run(CreateServiceClientUseCase(ctx).execute(scopes=["storage:read"]))
    return result.client_id, result.client_secret


def test_oauth_token_issues_service_token(ctx) -> None:
    from api.main import create_app

    client_id, secret = _create_client(ctx)
    app = TestClient(create_app(ctx))
    r = app.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": secret,
            "scope": "storage:read",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["scope"] == "storage:read"


def test_oauth_token_accepts_form_urlencoded(ctx) -> None:
    from api.main import create_app

    client_id, secret = _create_client(ctx)
    app = TestClient(create_app(ctx))
    r = app.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": secret,
            "scope": "storage:read",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["scope"] == "storage:read"


def test_oauth_token_bad_credentials_401(ctx) -> None:
    from api.main import create_app

    app = TestClient(create_app(ctx))
    r = app.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": "not-a-client",
            "client_secret": "bad-secret",
            "scope": "storage:read",
        },
    )
    assert r.status_code == 401


def test_oauth_token_unsupported_grant_400(ctx) -> None:
    from api.main import create_app

    app = TestClient(create_app(ctx))
    r = app.post(
        "/oauth/token",
        json={
            "grant_type": "password",
            "client_id": "x",
            "client_secret": "y",
            "scope": "storage:read",
        },
    )
    assert r.status_code == 400
