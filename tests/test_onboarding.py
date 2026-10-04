"""Tests de onboarding: nick único + aceptación legal versionada + reaceptación."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from application.context import AuthContext
from domain.exceptions import InvalidNicknameError
from domain.services import nickname as nick

TERMS = "2026-10-01"
PRIVACY = "2026-10-01"


def _login(app: TestClient, email: str, password: str = "s3cret-password") -> str:
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


def _onboard(app: TestClient, token: str, nickname: str) -> object:
    return app.post(
        "/auth/onboarding",
        json={"nickname": nickname, "terms_version": TERMS, "privacy_version": PRIVACY},
        headers=_auth(token),
    )


# --- reglas de nickname --------------------------------------------------------


def test_nickname_normalize_and_validate() -> None:
    assert nick.normalize("  Miguel ") == "miguel"
    assert nick.validate("mgarcia") == "mgarcia"
    assert nick.validate("a_b") == "a_b"
    assert nick.validate("Miguel-2026") == "miguel-2026"

    for bad in ("ab", "-abc", "abc-", "a" * 31, "m.garcia", "josé", "admin"):
        with pytest.raises(InvalidNicknameError):
            nick.validate(bad)


# --- endpoints -----------------------------------------------------------------


def test_legal_current_is_public(app: TestClient) -> None:
    r = app.get("/auth/legal/current")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "terms_version": TERMS,
        "privacy_version": PRIVACY,
        "terms_url": "/terms",
        "privacy_url": "/privacy",
    }


def test_new_user_requires_onboarding(app: TestClient) -> None:
    token = _login(app, "new@example.com")
    me = app.get("/auth/me", headers=_auth(token)).json()
    assert me["nickname"] is None
    assert me["onboarding"]["required"] is True
    assert me["onboarding"]["nickname_set"] is False
    assert me["onboarding"]["terms_accepted"] is False
    assert me["onboarding"]["privacy_accepted"] is False


def test_onboarding_requires_auth(app: TestClient) -> None:
    r = app.post(
        "/auth/onboarding",
        json={"nickname": "mgarcia", "terms_version": TERMS, "privacy_version": PRIVACY},
    )
    assert r.status_code == 401


def test_onboarding_success_and_me_reflects_it(app: TestClient) -> None:
    token = _login(app, "ok@example.com")
    r = _onboard(app, token, "mgarcia")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nickname"] == "mgarcia"
    assert body["onboarding"]["required"] is False
    assert body["onboarding"]["terms_accepted"] is True
    assert body["onboarding"]["privacy_accepted"] is True

    me = app.get("/auth/me", headers=_auth(token)).json()
    assert me["onboarding"]["required"] is False
    assert me["nickname"] == "mgarcia"


def test_onboarding_invalid_nickname_422(app: TestClient) -> None:
    token = _login(app, "bad@example.com")
    r = _onboard(app, token, "ab")
    assert r.status_code == 422


def test_onboarding_nickname_taken_409(app: TestClient) -> None:
    first = _login(app, "first@example.com")
    assert _onboard(app, first, "mgarcia").status_code == 200

    second = _login(app, "second@example.com")
    r = _onboard(app, second, "MGARCIA")  # casefold → colisión
    assert r.status_code == 409


def test_onboarding_stale_legal_version_409(app: TestClient) -> None:
    token = _login(app, "stale@example.com")
    r = app.post(
        "/auth/onboarding",
        json={"nickname": "staleuser", "terms_version": "1999-01-01", "privacy_version": PRIVACY},
        headers=_auth(token),
    )
    assert r.status_code == 409


def test_reacceptance_required_after_version_bump(app: TestClient, ctx: AuthContext) -> None:
    token = _login(app, "bump@example.com")
    assert _onboard(app, token, "bumpuser").status_code == 200
    assert app.get("/auth/me", headers=_auth(token)).json()["onboarding"]["required"] is False

    ctx.settings.terms_version = "2027-01-01"  # nueva versión vigente → reaceptación

    state = app.get("/auth/me", headers=_auth(token)).json()["onboarding"]
    assert state["required"] is True
    assert state["terms_accepted"] is False
    assert state["privacy_accepted"] is True
    assert state["terms_version_current"] == "2027-01-01"


def test_freshly_created_user_requires_onboarding() -> None:
    """Tanto el registro por contraseña como el social crean el usuario con `User.new`:
    ambos parten sin nickname ni términos → onboarding requerido."""
    from domain.entities.user import User

    user = User.new(
        email_lookup="x", email_cipher=b"c", password_hash="", key_version=1, name="X"
    )
    assert user.onboarding_required(terms_version=TERMS, privacy_version=PRIVACY) is True
