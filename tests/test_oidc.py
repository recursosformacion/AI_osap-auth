"""Tests del flujo OIDC (Authorization Code + PKCE) de osap-auth como IdP."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from application.context import AuthContext
from domain.entities.oauth_client import OAuthClient
from domain.util import pkce_challenge

CLIENT_ID = "osap-api"
CLIENT_SECRET = "rp-secret-value"
REDIRECT_URI = "https://api.example.com/auth/oidc/callback"


async def _seed_client(ctx: AuthContext) -> None:
    client = OAuthClient.new(
        client_id=CLIENT_ID,
        client_secret_hash=ctx.token_hasher.hash(CLIENT_SECRET),
        redirect_uris=[REDIRECT_URI],
        pkce_required=True,
        token_endpoint_auth_method="client_secret_post",
    )
    await ctx.oauth_clients.save(client)


def _setup_user(app: TestClient) -> dict:
    r = app.post(
        "/auth/register", json={"email": "oidc@example.com", "password": "s3cret-password"}
    )
    assert r.status_code == 201
    token = r.json()["verification_token"]
    assert app.post("/auth/verify-email", json={"token": token}).status_code == 200
    r = app.post("/auth/login", json={"email": "oidc@example.com", "password": "s3cret-password"})
    assert r.status_code == 200
    return r.json()


def _login_url() -> str:
    return (
        f"/auth/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&scope=openid%20profile&state=csrf&nonce=n1"
        f"&code_challenge={pkce_challenge('verifier')}&code_challenge_method=S256"
    )


def test_well_known_discovery(app: TestClient) -> None:
    r = app.get("/.well-known/openid-configuration")
    assert r.status_code == 200
    body = r.json()
    assert body["issuer"] == "https://auth.osap"
    assert body["authorization_endpoint"].endswith("/auth/authorize")
    assert body["token_endpoint"].endswith("/oauth/token")
    assert "code" in body["response_types_supported"]
    assert "S256" in body["code_challenge_methods_supported"]
    assert "authorization_code" in body["grant_types_supported"]
    assert "refresh_token" in body["grant_types_supported"]


async def test_authorize_redirects_to_login(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    r = app.get(_login_url(), follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login?" in r.headers["location"]


async def test_authorize_unknown_client_400(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    r = app.get(_login_url().replace(str(CLIENT_ID), str(uuid.uuid4())))
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_client"


async def test_authorize_bad_redirect_uri_400(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    url = (
        f"/auth/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri=https://evil.example.com/cb&scope=openid"
    )
    r = app.get(url)
    assert r.status_code == 400


async def test_authorize_accepts_redirect_by_domain(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    # Mismo host permitido, distinta ruta: se acepta (validación por dominio).
    url = (
        f"/auth/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri=https://api.example.com/other/callback&scope=openid"
        f"&code_challenge=x&code_challenge_method=S256"
    )
    r = app.get(url, follow_redirects=False)
    assert r.status_code == 302


async def test_authorize_rejects_other_domain(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    url = (
        f"/auth/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri=https://evil.example.net/cb&scope=openid&code_challenge=x"
    )
    r = app.get(url, follow_redirects=False)
    assert r.status_code == 400


async def test_authorize_requires_pkce(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    url = (
        f"/auth/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&scope=openid"
    )
    r = app.get(url, follow_redirects=False)
    assert r.status_code == 302
    assert "error=invalid_request" in r.headers["location"]


def _complete(app: TestClient, access_token: str) -> dict:
    r = app.post(
        "/auth/authorize/complete",
        json={
            "client_id": str(CLIENT_ID),
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile",
            "state": "csrf",
            "nonce": "n1",
            "code_challenge": pkce_challenge("verifier"),
            "code_challenge_method": "S256",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _token_payload(code: str) -> dict:
    return {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": "verifier",
        "redirect_uri": REDIRECT_URI,
        "client_id": str(CLIENT_ID),
        "client_secret": CLIENT_SECRET,
    }


async def test_full_flow(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    user = _setup_user(app)
    completed = _complete(app, user["access_token"])
    assert completed["redirect_uri"] == REDIRECT_URI
    assert completed["state"] == "csrf"
    assert completed["code"]

    r = app.post("/oauth/token", data=_token_payload(completed["code"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    claims = ctx.token_provider.verify_access_token(
        body["access_token"], expected_audience=str(CLIENT_ID)
    )
    assert claims["sub"] == user["user_id"]
    assert claims["token_use"] == "user"
    assert claims["aud"] == str(CLIENT_ID)
    assert claims["nonce"] == "n1"


async def test_code_single_use(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    user = _setup_user(app)
    completed = _complete(app, user["access_token"])
    payload = _token_payload(completed["code"])
    assert app.post("/oauth/token", data=payload).status_code == 200
    r = app.post("/oauth/token", data=payload)
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_grant"


async def test_pkce_verifier_mismatch(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    user = _setup_user(app)
    completed = _complete(app, user["access_token"])
    payload = _token_payload(completed["code"])
    payload["code_verifier"] = "wrong-verifier"
    r = app.post("/oauth/token", data=payload)
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_grant"


async def test_bad_client_secret(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    user = _setup_user(app)
    completed = _complete(app, user["access_token"])
    payload = _token_payload(completed["code"])
    payload["client_secret"] = "wrong-secret"
    r = app.post("/oauth/token", data=payload)
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_client"


async def test_refresh_token_flow(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    user = _setup_user(app)
    completed = _complete(app, user["access_token"])
    tok = app.post("/oauth/token", data=_token_payload(completed["code"])).json()

    r = app.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "client_id": str(CLIENT_ID),
            "client_secret": CLIENT_SECRET,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"] != tok["refresh_token"]
    claims = ctx.token_provider.verify_access_token(
        body["access_token"], expected_audience=str(CLIENT_ID)
    )
    assert claims["aud"] == str(CLIENT_ID)


async def test_refresh_reuse_detected(ctx: AuthContext, app: TestClient) -> None:
    await _seed_client(ctx)
    user = _setup_user(app)
    completed = _complete(app, user["access_token"])
    tok = app.post("/oauth/token", data=_token_payload(completed["code"])).json()
    refresh = tok["refresh_token"]
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": str(CLIENT_ID),
        "client_secret": CLIENT_SECRET,
    }
    assert app.post("/oauth/token", data=payload).status_code == 200
    r = app.post("/oauth/token", data=payload)
    assert r.status_code == 401
