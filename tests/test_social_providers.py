"""Parámetros del authorize de los proveedores sociales."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from infrastructure.social.providers import GitHubProvider, GoogleProvider


def _query(provider: GoogleProvider | GitHubProvider) -> dict[str, list[str]]:
    url = provider.authorize_url("https://app.example/callback", "state", "challenge")
    return parse_qs(urlparse(url).query)


def test_google_fuerza_selector_de_cuenta() -> None:
    query = _query(GoogleProvider(client_id="id", client_secret="secret"))

    assert query["prompt"] == ["select_account"]
    assert query["code_challenge_method"] == ["S256"]


def test_github_no_usa_prompt_de_google() -> None:
    query = _query(GitHubProvider(client_id="id", client_secret="secret"))

    assert "prompt" not in query
