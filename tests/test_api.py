"""Tests de integración de la API HTTP de osap-auth."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(
    client: TestClient, email: str = "user@example.com", password: str = "s3cret-password"
) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201
    return r.json()


def test_version_endpoint(app: TestClient) -> None:
    r = app.get("/auth/version")
    assert r.status_code == 200
    assert r.json() == {"contract": "osap-auth-v1", "version": "1.0"}


def test_jwks_endpoint(app: TestClient) -> None:
    r = app.get("/auth/.well-known/jwks.json")
    assert r.status_code == 200
    assert r.json()["keys"][0]["use"] == "sig"


def test_register_then_verify_then_login(app: TestClient) -> None:
    data = _register(app)
    assert data["verification_token"] is not None

    # Verificar email.
    r = app.post("/auth/verify-email", json={"token": data["verification_token"]})
    assert r.status_code == 200

    # Login.
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "s3cret-password"})
    assert r.status_code == 200
    body = r.json()
    assert body["email_verified"] is True
    assert body["access_token"]
    assert body["refresh_token"]


def test_register_duplicate_is_generic(app: TestClient) -> None:
    _register(app)
    r = app.post(
        "/auth/register", json={"email": "user@example.com", "password": "s3cret-password"}
    )
    # Genérico: mismo código, sin revelar existencia, sin token nuevo.
    assert r.status_code == 201
    assert r.json()["verification_token"] is None


def test_login_wrong_password_401(app: TestClient) -> None:
    _register(app)
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_login_unknown_401(app: TestClient) -> None:
    r = app.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever-password"}
    )
    assert r.status_code == 401


def test_me_requires_token(app: TestClient) -> None:
    r = app.get("/auth/me")
    assert r.status_code == 401


def test_me_with_token(app: TestClient) -> None:
    _register(app)
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "s3cret-password"})
    token = r.json()["access_token"]
    r = app.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"


def test_refresh_flow(app: TestClient) -> None:
    _register(app)
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "s3cret-password"})
    refresh = r.json()["refresh_token"]
    r = app.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_refresh_reuse_detected(app: TestClient) -> None:
    _register(app)
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "s3cret-password"})
    first = r.json()["refresh_token"]
    app.post("/auth/refresh", json={"refresh_token": first})
    # Reutilizar el rotado: 401.
    r = app.post("/auth/refresh", json={"refresh_token": first})
    assert r.status_code == 401


def test_logout_all_and_revocation(app: TestClient) -> None:
    _register(app)
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "s3cret-password"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = app.get("/auth/sessions", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = app.post("/auth/logout-all", headers=headers)
    assert r.status_code == 200


def test_password_reset_request_generic(app: TestClient) -> None:
    # Sin cuenta previa: 202 genérico.
    r = app.post("/auth/password-reset/request", json={"email": "ghost@example.com"})
    assert r.status_code == 202


def test_delete_account(app: TestClient) -> None:
    _register(app)
    r = app.post("/auth/login", json={"email": "user@example.com", "password": "s3cret-password"})
    token = r.json()["access_token"]
    r = app.delete("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
