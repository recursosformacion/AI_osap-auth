"""Tests del lookoup M2M de nombres visibles (`GET /auth/m2m/users`)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi.testclient import TestClient

from api.main import create_app
from application.use_cases.service_clients import CreateServiceClientUseCase
from domain.entities.user import UserStatus

SCOPE = "auth:read_public_names"
AUDIENCE = "osap-auth"


def _run(awaitable: Any) -> Any:
    return asyncio.run(awaitable)


def _create_client(ctx: Any, scopes: list[str], audiences: list[str]) -> tuple[str, str]:
    result = _run(
        CreateServiceClientUseCase(ctx).execute(scopes=scopes, allowed_audiences=audiences)
    )
    return result.client_id, result.client_secret


def _seed_user(ctx: Any, name: str | None, status: UserStatus | None = None) -> Any:
    from domain.entities.user import User

    user = User.new(
        email_lookup=f"lookup-{name}",
        email_cipher=b"cipher",
        password_hash="hash",
        key_version=1,
        name=name,
    )
    if status is not None:
        user.status = status
    _run(ctx.users.save(user))
    return user


def _service_token(app: TestClient, client_id: str, secret: str, scope: str = SCOPE,
                   audience: str = AUDIENCE) -> str:
    r = app.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": secret,
            "scope": scope,
            "audience": audience,
        },
    )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def test_lookup_returns_only_id_and_name_and_omits_missing(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, [SCOPE], [AUDIENCE])
    alice = _seed_user(ctx, "Alice")
    bob = _seed_user(ctx, "Bob")
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret)

    r = app.get(
        f"/auth/m2m/users?ids={alice.id},{bob.id},00000000-0000-0000-0000-000000000000,no-uuid",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert {item["id"] for item in body} == {str(alice.id), str(bob.id)}
    assert all(
        set(item.keys()) == {"id", "name", "nickname", "nickname_public_consent"}
        for item in body
    )
    assert {item["name"] for item in body} == {"Alice", "Bob"}


def test_lookup_requires_service_token(ctx: Any) -> None:
    app = TestClient(create_app(ctx))
    r = app.get("/auth/m2m/users?ids=00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401


def test_lookup_rejects_insufficient_scope(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, ["api:read", SCOPE], [AUDIENCE])
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret, scope="api:read")

    r = app.get(
        "/auth/m2m/users?ids=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403


def test_lookup_rejects_wrong_audience(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, [SCOPE], ["osap-support"])
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret, audience="osap-support")

    r = app.get(
        "/auth/m2m/users?ids=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 401


def test_lookup_returns_disabled_but_omits_deleted(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, [SCOPE], [AUDIENCE])
    active = _seed_user(ctx, "Active")
    disabled = _seed_user(ctx, "Disabled", status=UserStatus.DISABLED)
    deleted = _seed_user(ctx, "Deleted", status=UserStatus.DELETED)
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret)

    r = app.get(
        f"/auth/m2m/users?ids={active.id},{disabled.id},{deleted.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200, r.text
    ids = {item["id"] for item in r.json()}
    assert ids == {str(active.id), str(disabled.id)}


def test_lookup_rejects_more_than_max(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, [SCOPE], [AUDIENCE])
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret)
    ids = ",".join(str(uuid.uuid4()) for _ in range(501))

    r = app.get(f"/auth/m2m/users?ids={ids}", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 422


def test_lookup_empty_ids_returns_empty(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, [SCOPE], [AUDIENCE])
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret)

    r = app.get("/auth/m2m/users?ids=", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200 and r.json() == []


def _seed_public_user(ctx: Any, nickname: str, *, consent: bool = True,
                      status: UserStatus | None = None) -> Any:
    user = _seed_user(ctx, nickname)
    user.nickname = nickname
    user.nickname_public_consent = consent
    if status is not None:
        user.status = status
    _run(ctx.users.save(user))
    return user


def test_public_users_lists_only_consented_with_nickname(ctx: Any) -> None:
    client_id, secret = _create_client(ctx, [SCOPE], [AUDIENCE])
    alice = _seed_public_user(ctx, "alice")
    _seed_public_user(ctx, "bob", consent=False)  # sin consentimiento: no aparece
    cara = _seed_public_user(ctx, "cara")
    _seed_public_user(ctx, "deleted", status=UserStatus.DELETED)  # eliminado: no aparece
    app = TestClient(create_app(ctx))
    token = _service_token(app, client_id, secret)

    r = app.get("/auth/m2m/public-users", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert {item["id"] for item in body} == {str(alice.id), str(cara.id)}
    assert all(set(item.keys()) == {"id", "nickname"} for item in body)
    assert {item["nickname"] for item in body} == {"alice", "cara"}


def test_public_users_requires_service_token(ctx: Any) -> None:
    app = TestClient(create_app(ctx))
    assert app.get("/auth/m2m/public-users").status_code == 401
