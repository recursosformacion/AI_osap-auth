"""Autorización pública del nickname: usuario y admin (auditada por separado)."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient

from application.context import AuthContext


def _register_and_login(app: TestClient, email: str, password: str = "s3cret-password") -> str:
    reg = app.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201, reg.text
    token = reg.json().get("verification_token")
    if token:
        app.post("/auth/verify-email", json={"token": token})
    r = app.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_user_can_toggle_public_consent(app: TestClient) -> None:
    token = _register_and_login(app, "consent@example.com")
    # Opt-out: la visibilidad pública viene marcada por defecto al registrarse.
    assert app.get("/auth/me", headers=_auth(token)).json()["nickname_public_consent"] is True

    r = app.put("/auth/me/public-consent", json={"value": False}, headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["nickname_public_consent"] is False
    assert app.get("/auth/me", headers=_auth(token)).json()["nickname_public_consent"] is False

    r2 = app.put("/auth/me/public-consent", json={"value": True}, headers=_auth(token))
    assert r2.json()["nickname_public_consent"] is True


def test_admin_can_toggle_public_consent(app: TestClient, ctx: AuthContext) -> None:
    admin_token = _register_and_login(app, "admin@example.com")
    admin_id = app.get("/auth/me", headers=_auth(admin_token)).json()["user_id"]
    admin_user = asyncio.run(ctx.users.get_by_id(uuid.UUID(admin_id)))
    assert admin_user is not None
    admin_user.roles = ["admin"]
    asyncio.run(ctx.users.save(admin_user))
    admin_token = app.post(
        "/auth/login", json={"email": "admin@example.com", "password": "s3cret-password"}
    ).json()["access_token"]

    target_token = _register_and_login(app, "target@example.com")
    target_id = app.get("/auth/me", headers=_auth(target_token)).json()["user_id"]

    r = app.put(
        f"/auth/admin/users/{target_id}/public-consent",
        json={"value": True},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["nickname_public_consent"] is True
    assert (
        app.get(f"/auth/admin/users/{target_id}", headers=_auth(admin_token)).json()[
            "nickname_public_consent"
        ]
        is True
    )
