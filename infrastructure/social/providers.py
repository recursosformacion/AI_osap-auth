"""Proveedores sociales (upstream) de osap-auth: Google y GitHub.

Usan OAuth2/OIDC Authorization Code + PKCE. Necesitan credenciales reales
(client_id/client_secret) en config.yaml para funcionar en vivo.
"""

from __future__ import annotations

import httpx

from domain.ports.social import ProviderProfile, SocialProvider


class BaseOAuthProvider(SocialProvider):
    def __init__(self, *, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def authorize_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        import urllib.parse

        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.authorize_endpoint}?{urllib.parse.urlencode(params)}"

    async def exchange_and_profile(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> ProviderProfile:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                self.token_endpoint, data=data, headers={"Accept": "application/json"}
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("no access_token del proveedor")

            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            if self.accept_header:
                headers["Accept"] = self.accept_header
            user_resp = await client.get(self.userinfo_endpoint, headers=headers)
            user_resp.raise_for_status()
            return self._profile_from_userinfo(user_resp.json())

    def _profile_from_userinfo(self, user: dict) -> ProviderProfile:
        raise NotImplementedError

    @property
    def authorize_endpoint(self) -> str:
        raise NotImplementedError

    @property
    def token_endpoint(self) -> str:
        raise NotImplementedError

    @property
    def userinfo_endpoint(self) -> str:
        raise NotImplementedError

    @property
    def scope(self) -> str:
        raise NotImplementedError

    @property
    def accept_header(self) -> str:
        return "application/json"


class GoogleProvider(BaseOAuthProvider):
    name = "google"

    @property
    def authorize_endpoint(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_endpoint(self) -> str:
        return "https://oauth2.googleapis.com/token"

    @property
    def userinfo_endpoint(self) -> str:
        return "https://openidconnect.googleapis.com/v1/userinfo"

    @property
    def scope(self) -> str:
        return "openid email profile"

    def _profile_from_userinfo(self, user: dict) -> ProviderProfile:
        email = user.get("email")
        return ProviderProfile(
            sub=str(user.get("sub", "")),
            email=email or None,
            name=user.get("name"),
            email_verified=bool(user.get("email_verified", False)),
        )


class GitHubProvider(BaseOAuthProvider):
    name = "github"

    @property
    def authorize_endpoint(self) -> str:
        return "https://github.com/login/oauth/authorize"

    @property
    def token_endpoint(self) -> str:
        return "https://github.com/login/oauth/access_token"

    @property
    def userinfo_endpoint(self) -> str:
        return "https://api.github.com/user"

    @property
    def scope(self) -> str:
        return "read:user user:email"

    @property
    def accept_header(self) -> str:
        return "application/vnd.github+json"

    async def exchange_and_profile(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> ProviderProfile:
        profile = await super().exchange_and_profile(code, redirect_uri, code_verifier)
        # GitHub no expone email_verified y el email puede venir vacío: resolver email primario.
        if not profile.email:
            profile.email = await self._resolve_primary_email(code, redirect_uri, code_verifier)
        profile.email_verified = False
        return profile

    async def _resolve_primary_email(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> str | None:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                self.token_endpoint, data=data, headers={"Accept": "application/json"}
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")
            if not access_token:
                return None
            emails = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if emails.status_code != 200:
                return None
            for entry in emails.json():
                if entry.get("primary"):
                    return entry.get("email")
        return None

    def _profile_from_userinfo(self, user: dict) -> ProviderProfile:
        return ProviderProfile(
            sub=str(user.get("id", "")),
            email=user.get("email") or None,
            name=user.get("name") or user.get("login"),
            email_verified=False,
        )
