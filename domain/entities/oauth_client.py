"""Cliente OAuth2/OIDC (relying party) de osap-auth.

Registra a las aplicaciones que actúan como *relying party* (p.ej. osap-api) para el
flujo Authorization Code + PKCE. El secreto solo se guarda hasheado.
"""

from __future__ import annotations

import urllib.parse
from datetime import UTC, datetime

OIDC_SCOPES: tuple[str, ...] = ("openid", "profile", "email")
DEFAULT_GRANT_TYPES: tuple[str, ...] = ("authorization_code", "refresh_token")


class OAuthClient:
    """Cliente RP que puede iniciar un flujo OIDC Authorization Code + PKCE.

    La `redirect_uri` no se valida por URL fija sino por **dominio**: se acepta cualquier
    `redirect_uri` cuyo host coincida (o sea subdominio) con uno de `allowed_redirect_hosts`.
    Así el cliente envía su `redirect_uri` en cada petición (desde su configuración) y osap-auth
    solo verifica el dominio, sin quedar atado a una aplicación concreta.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret_hash: str,
        redirect_uris: list[str],
        allowed_redirect_hosts: list[str],
        grant_types: list[str],
        response_types: list[str],
        allowed_scopes: list[str],
        pkce_required: bool,
        token_endpoint_auth_method: str,
        enabled: bool,
        created_at: datetime | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret_hash = client_secret_hash
        self.redirect_uris = redirect_uris
        self.allowed_redirect_hosts = allowed_redirect_hosts
        self.grant_types = grant_types
        self.response_types = response_types
        self.allowed_scopes = allowed_scopes
        self.pkce_required = pkce_required
        self.token_endpoint_auth_method = token_endpoint_auth_method
        self.enabled = enabled
        self.created_at = created_at

    def allows_redirect_uri(self, redirect_uri: str) -> bool:
        parsed = urllib.parse.urlparse(redirect_uri)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        if redirect_uri in self.redirect_uris:
            return True
        for allowed in self.allowed_redirect_hosts:
            allowed_host = allowed.strip().lower()
            if host == allowed_host or host.endswith("." + allowed_host):
                return True
        return False

    def allows_grant(self, grant_type: str) -> bool:
        return grant_type in self.grant_types

    def allows_response_type(self, response_type: str) -> bool:
        return response_type in self.response_types

    def allows_scope(self, scope: str) -> bool:
        scopes = [s for s in scope.split() if s]
        return all(s in self.allowed_scopes for s in scopes)

    @classmethod
    def new(
        cls,
        *,
        client_id: str,
        client_secret_hash: str,
        redirect_uris: list[str],
        allowed_redirect_hosts: list[str] | None = None,
        grant_types: list[str] | None = None,
        response_types: list[str] | None = None,
        allowed_scopes: list[str] | None = None,
        pkce_required: bool = True,
        token_endpoint_auth_method: str = "client_secret_post",
    ) -> OAuthClient:
        hosts = (
            allowed_redirect_hosts
            if allowed_redirect_hosts is not None
            else _hosts_from(redirect_uris)
        )
        return cls(
            client_id=client_id,
            client_secret_hash=client_secret_hash,
            redirect_uris=redirect_uris,
            allowed_redirect_hosts=hosts,
            grant_types=grant_types or list(DEFAULT_GRANT_TYPES),
            response_types=response_types or ["code"],
            allowed_scopes=allowed_scopes or list(OIDC_SCOPES),
            pkce_required=pkce_required,
            token_endpoint_auth_method=token_endpoint_auth_method,
            enabled=True,
            created_at=datetime.now(UTC),
        )


def _hosts_from(redirect_uris: list[str]) -> list[str]:
    hosts: list[str] = []
    for uri in redirect_uris:
        host = urllib.parse.urlparse(uri).hostname
        if host and host not in hosts:
            hosts.append(host)
    return hosts
