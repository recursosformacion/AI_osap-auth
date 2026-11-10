"""Tests del teléfono voluntario del usuario (comunicaciones por WhatsApp)."""

from __future__ import annotations

from fastapi.testclient import TestClient

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


def _onboard(app: TestClient, token: str, nickname: str, phone: str | None = None) -> object:
    payload: dict[str, object] = {
        "nickname": nickname,
        "terms_version": TERMS,
        "privacy_version": PRIVACY,
    }
    if phone is not None:
        payload["phone"] = phone
    return app.post("/auth/onboarding", json=payload, headers=_auth(token))


def test_onboarding_stores_normalized_phone(app: TestClient) -> None:
    token = _login(app, "phone-onboarding@example.com")
    r = _onboard(app, token, "contelefono", "+34 600-123-456")
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "+34600123456"

    me = app.get("/auth/me", headers=_auth(token)).json()
    assert me["phone"] == "+34600123456"


def test_phone_is_optional_in_onboarding(app: TestClient) -> None:
    token = _login(app, "phone-optional@example.com")
    r = _onboard(app, token, "sintelefono")
    assert r.status_code == 200, r.text
    assert r.json()["phone"] is None


def test_update_and_clear_phone(app: TestClient) -> None:
    token = _login(app, "phone-update@example.com")
    assert _onboard(app, token, "actualizatel").status_code == 200

    updated = app.put(
        "/auth/me/phone", json={"phone": "0034600123456"}, headers=_auth(token)
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["phone"] == "+34600123456"

    cleared = app.put("/auth/me/phone", json={"phone": None}, headers=_auth(token))
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["phone"] is None


def test_invalid_phone_is_422(app: TestClient) -> None:
    token = _login(app, "phone-bad@example.com")
    assert _onboard(app, token, "maltelefono").status_code == 200

    r = app.put("/auth/me/phone", json={"phone": "123"}, headers=_auth(token))
    assert r.status_code == 422

    r = _onboard(app, _login(app, "phone-bad-2@example.com"), "maltelefono2", "abc")
    assert r.status_code == 422


def test_phone_requires_auth(app: TestClient) -> None:
    assert app.put("/auth/me/phone", json={"phone": "600123456"}).status_code == 401
