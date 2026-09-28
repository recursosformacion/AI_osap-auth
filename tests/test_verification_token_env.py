"""Tests de A5: entorno efectivo y emisión de verification_token.

- El entorno efectivo se resuelve con la misma precedencia que el resto de la config
  (OSAP_AUTH_ENV > app.env > production fail-closed).
- El token de verificación solo se devuelve en development/test; nunca en producción.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from infrastructure.config import resolve_config_env
from tests.fakes import make_context

_PASSWORD = "s3cret-password"


def _client_for_env(env: str) -> TestClient:
    ctx, _ = make_context()
    ctx.settings.env = env
    return TestClient(create_app(ctx))


def _register(client: TestClient, email: str = "v@example.com") -> httpx.Response:
    return client.post("/auth/register", json={"email": email, "password": _PASSWORD})


@pytest.mark.parametrize("env", ["development", "test"])
def test_dev_y_test_devuelven_verification_token(env: str) -> None:
    r = _register(_client_for_env(env))
    assert r.status_code == 201
    assert r.json().get("verification_token")


def test_produccion_nunca_devuelve_verification_token() -> None:
    r = _register(_client_for_env("production"))
    assert r.status_code == 201
    assert r.json().get("verification_token") is None


def test_env_osap_auth_env_tiene_prioridad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_AUTH_ENV", "production")
    assert resolve_config_env({"app": {"env": "development"}}) == "production"


def test_env_app_env_se_usa_si_no_hay_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OSAP_AUTH_ENV", raising=False)
    assert resolve_config_env({"app": {"env": "test"}}) == "test"


def test_env_sin_marca_falla_cerrado(monkeypatch: pytest.MonkeyPatch) -> None:
    # Producción real no puede caer accidentalmente en el camino de desarrollo.
    monkeypatch.delenv("OSAP_AUTH_ENV", raising=False)
    assert resolve_config_env({}) == "production"
