"""Tests del login social (upstream) de osap-auth."""

from __future__ import annotations

import pytest

from application.context import AuthContext
from application.use_cases.social_login import (
    SocialLoginCallbackUseCase,
    SocialLoginStartUseCase,
)
from domain.entities.oauth_client import OAuthClient
from domain.exceptions import OAuthError
from domain.ports.social import ProviderProfile, SocialProvider
from tests.fakes import (
    FakeOAuthClientRepository,
    FakeProviderAccountRepository,
    make_context,
)

CLIENT_ID = "osap-api"
CLIENT_SECRET = "rp-secret"
REDIRECT = "https://api.example.com/api/v1/auth/oidc/callback"


class FakeProvider(SocialProvider):
    name = "google"

    def __init__(self, profile: ProviderProfile | None = None) -> None:
        self._profile = profile or ProviderProfile(
            sub="google-123", email="social@example.com", name="Social User", email_verified=True
        )

    def authorize_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        return f"https://provider/authorize?state={state}"

    async def exchange_and_profile(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> ProviderProfile:
        return self._profile


async def _make_ctx(profile: ProviderProfile | None = None) -> AuthContext:
    oauth_clients = FakeOAuthClientRepository()
    client = OAuthClient.new(
        client_id=CLIENT_ID,
        client_secret_hash="unused",
        redirect_uris=[REDIRECT],
        pkce_required=True,
    )
    await oauth_clients.save(client)
    ctx, _ = make_context(
        oauth_clients=oauth_clients,
        provider_accounts=FakeProviderAccountRepository(),
        social_providers={"google": FakeProvider(profile)},
    )
    return ctx


@pytest.mark.asyncio
async def test_start_returns_provider_url() -> None:
    ctx = await _make_ctx()
    url = await SocialLoginStartUseCase(ctx).execute(provider="google", params={})
    assert url.startswith("https://provider/authorize?state=")


@pytest.mark.asyncio
async def test_start_unknown_provider() -> None:
    ctx = await _make_ctx()
    with pytest.raises(OAuthError):
        await SocialLoginStartUseCase(ctx).execute(provider="github", params={})


@pytest.mark.asyncio
async def test_start_validates_downstream_context() -> None:
    ctx = await _make_ctx()
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": "openid profile",
        "code_challenge": "x",
        "code_challenge_method": "S256",
    }
    url = await SocialLoginStartUseCase(ctx).execute(provider="google", params=params)
    assert url.startswith("https://provider/authorize?state=")


@pytest.mark.asyncio
async def test_callback_creates_user_and_completes_downstream() -> None:
    ctx = await _make_ctx()
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": "openid profile",
        "state": "downstream-state",
        "nonce": "n1",
        "code_challenge": "x",
        "code_challenge_method": "S256",
    }
    start = await SocialLoginStartUseCase(ctx).execute(provider="google", params=params)
    state_token = start.split("state=", 1)[1]

    result = await SocialLoginCallbackUseCase(ctx).execute(
        provider="google",
        code="auth-code",
        state_token=state_token,
        ip="1.2.3.4",
        user_agent="test",
    )
    assert result.redirect_uri.startswith(REDIRECT)
    assert "code=" in result.redirect_uri
    assert "state=downstream-state" in result.redirect_uri

    users = await ctx.users.list_all()
    assert len(users) == 1
    assert users[0].email_verified is True
    account = await ctx.provider_accounts.get_by_provider_sub("google", "google-123")
    assert account is not None
    assert account.user_id == users[0].id


@pytest.mark.asyncio
async def test_callback_links_existing_user() -> None:
    ctx = await _make_ctx()
    # Primera vez crea.
    params = {"client_id": CLIENT_ID, "redirect_uri": REDIRECT, "response_type": "code",
              "scope": "openid profile", "code_challenge": "x", "code_challenge_method": "S256"}
    start = await SocialLoginStartUseCase(ctx).execute(provider="google", params=params)
    state1 = start.split("state=", 1)[1]
    await SocialLoginCallbackUseCase(ctx).execute(
        provider="google", code="c1", state_token=state1, ip="1.2.3.4", user_agent="test"
    )
    user_id = (await ctx.provider_accounts.get_by_provider_sub("google", "google-123")).user_id

    # Segunda vez vincula a la misma cuenta.
    start2 = await SocialLoginStartUseCase(ctx).execute(provider="google", params=params)
    state2 = start2.split("state=", 1)[1]
    await SocialLoginCallbackUseCase(ctx).execute(
        provider="google", code="c2", state_token=state2, ip="1.2.3.4", user_agent="test"
    )
    assert len(await ctx.users.list_all()) == 1
    account = await ctx.provider_accounts.get_by_provider_sub("google", "google-123")
    assert account.user_id == user_id


@pytest.mark.asyncio
async def test_callback_without_downstream_redirects_to_login() -> None:
    ctx = await _make_ctx()
    start = await SocialLoginStartUseCase(ctx).execute(provider="google", params={})
    state_token = start.split("state=", 1)[1]
    result = await SocialLoginCallbackUseCase(ctx).execute(
        provider="google", code="c", state_token=state_token, ip=None, user_agent=None
    )
    assert result.redirect_uri.endswith("/auth/login")
    assert len(await ctx.users.list_all()) == 1
