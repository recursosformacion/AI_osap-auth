"""Tests de validación de configuración para osap-auth."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

try:
    from osap.bootstrap.configuration import ConfigurationError, ConfigurationWarning, validate_generic_service_config
except ImportError:
    pytest.skip("osap-api no instalado; instalar con pip install -e ../osap-api", allow_module_level=True)


_MINIMAL_AUTH_YAML = """
database:
  host: 127.0.0.1
  name: osap_auth
  user: osap_auth
  password: secret

crypto:
  email_hmac_pepper: pepper
  email_aead_key_b64: YWJj
  token_hmac_pepper: token
  jwt_private_key: key
  jwt_public_key: pub
  jwt_kid: osap-auth-v1

issuer: https://auth.osap
audience: osap-api
"""


def _write_yaml(tmp_path: Path, data: dict[str, object]) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data, encoding="utf-8"), encoding="utf-8")
    return p


def test_production_ok_when_minimal_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_ENV", "production")
    config_path = _write_yaml(tmp_path, yaml.safe_load(_MINIMAL_AUTH_YAML))
    validate_generic_service_config("osap-auth", yaml.safe_load(config_path.read_text(encoding="utf-8")), config_path)


def test_production_raises_when_database_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_ENV", "production")
    data = yaml.safe_load(_MINIMAL_AUTH_YAML)
    data["database"]["host"] = ""
    config_path = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigurationError, match="Campo obligatorio 'db.host'"):
        validate_generic_service_config("osap-auth", data, config_path)


def test_production_raises_when_crypto_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_ENV", "production")
    data = yaml.safe_load(_MINIMAL_AUTH_YAML)
    del data["crypto"]
    config_path = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigurationError, match="Sección obligatoria 'crypto'"):
        validate_generic_service_config("osap-auth", data, config_path)


def test_production_raises_when_issuer_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_ENV", "production")
    data = yaml.safe_load(_MINIMAL_AUTH_YAML)
    del data["issuer"]
    config_path = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigurationError, match="Campo obligatorio 'oidc.issuer'"):
        validate_generic_service_config("osap-auth", data, config_path)


def test_development_warns_but_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSAP_ENV", "development")
    data = yaml.safe_load(_MINIMAL_AUTH_YAML)
    del data["crypto"]
    config_path = _write_yaml(tmp_path, data)
    with pytest.warns(ConfigurationWarning, match="Sección recomendada 'crypto'"):
        validate_generic_service_config("osap-auth", data, config_path)
