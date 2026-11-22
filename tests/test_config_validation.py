"""Tests de la validación de configuración de arranque de osap-auth (S1, fail-closed).

Sustituye al contrato roto del validador compartido (`osap.bootstrap...`, nunca
implementado) por validación local. Nombres reales del `config.yaml`: `database.*`,
`crypto.jwt_*` y `key_version`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from infrastructure.config import (
    Settings,
    missing_required_keys,
    resolve_config_env,
    validate_startup_config,
)

_VALID: dict[str, object] = {
    "app": {"env": "production"},
    "database": {"host": "db", "name": "osap_auth", "user": "osap", "password": "secret"},
    "crypto": {
        "email_hmac_pepper": "email-pepper",
        "email_aead_key_b64": "YWJjZGVmZ2hpamtsbW5vcA==",
        "token_hmac_pepper": "token-pepper",
        "jwt_private_key": "-----BEGIN",
        "jwt_public_key": "-----BEGIN",
    },
    "smtp": {"host": "smtp.example.test", "from_address": "no-reply@example.test"},
    "key_version": "v1",
}


def _write(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _copy() -> dict[str, object]:
    return {k: dict(v) if isinstance(v, dict) else v for k, v in _VALID.items()}


@pytest.fixture(autouse=True)
def _no_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OSAP_AUTH_ENV", raising=False)
    for name in (
        "OSAP_AUTH_DB_HOST", "OSAP_AUTH_DB_NAME", "OSAP_AUTH_DB_USER", "OSAP_AUTH_DB_PASSWORD",
        "OSAP_AUTH_EMAIL_PEPPER", "OSAP_AUTH_EMAIL_AEAD_KEY", "OSAP_AUTH_TOKEN_PEPPER",
        "OSAP_AUTH_JWT_PRIVATE_KEY", "OSAP_AUTH_JWT_PUBLIC_KEY",
        "OSAP_AUTH_SMTP_HOST", "OSAP_AUTH_SMTP_FROM",
    ):
        monkeypatch.delenv(name, raising=False)


def test_configuracion_valida_en_produccion_arranca(tmp_path: Path) -> None:
    validate_startup_config(_write(tmp_path, _VALID))


@pytest.mark.parametrize(
    "path",
    [
        "database.host",
        "database.name",
        "database.user",
        "database.password",
        "crypto.email_hmac_pepper",
        "crypto.email_aead_key_b64",
        "crypto.token_hmac_pepper",
        "crypto.jwt_private_key",
        "crypto.jwt_public_key",
        "smtp.host",
        "smtp.from_address",
        "key_version",
    ],
)
def test_cada_clave_obligatoria_ausente_no_arranca(tmp_path: Path, path: str) -> None:
    data = _copy()
    if "." in path:
        section, key = path.split(".")
        del data[section][key]  # type: ignore[index]
    else:
        del data[path]
    with pytest.raises(SystemExit):
        validate_startup_config(_write(tmp_path, data))


def test_clave_vacia_no_arranca(tmp_path: Path) -> None:
    data = _copy()
    data["crypto"]["jwt_private_key"] = ""  # type: ignore[index]
    with pytest.raises(SystemExit):
        validate_startup_config(_write(tmp_path, data))


def test_sin_marca_de_entorno_falla_cerrado(tmp_path: Path) -> None:
    data = {"database": {"host": "db"}, "crypto": {}}
    with pytest.raises(SystemExit):
        validate_startup_config(_write(tmp_path, data))


def test_desarrollo_avisa_pero_arranca(tmp_path: Path) -> None:
    data = {"app": {"env": "development"}, "database": {}, "crypto": {}}
    validate_startup_config(_write(tmp_path, data))


def test_no_existe_el_camino_silencioso_de_import(tmp_path: Path) -> None:
    # Antes, cualquier fallo/import ausente devolvía sin validar. Ahora es obligatorio.
    data = {"app": {"env": "production"}, "database": {}, "crypto": {}, "key_version": ""}
    with pytest.raises(SystemExit):
        validate_startup_config(_write(tmp_path, data))


def test_helpers_de_introspeccion() -> None:
    assert resolve_config_env({"app": {"env": "test"}}) == "test"
    assert resolve_config_env({}) == "production"
    assert missing_required_keys(_VALID) == []


def test_jwt_kid_y_previous_se_leen_del_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OSAP_AUTH_JWT_KID", raising=False)
    monkeypatch.delenv("OSAP_AUTH_JWT_PREVIOUS_PUBLIC_KEYS", raising=False)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "app": {"env": "development"},
                "crypto": {
                    "jwt_kid": "osap-auth-v2",
                    "jwt_previous_public_keys": [
                        {"kid": "osap-auth-v1", "public_key": "PEM-V1"}
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    settings = Settings(config_file=config_file)
    assert settings.crypto.jwt_kid == "osap-auth-v2"
    assert settings.crypto.jwt_previous_public_keys == [
        {"kid": "osap-auth-v1", "public_key": "PEM-V1"}
    ]



def test_placeholders_secret_sin_resolver_no_se_aceptan(tmp_path: Path) -> None:
    data = _copy()
    data["database"]["password"] = "${OSAP_AUTH_DB_PASSWORD}"  # type: ignore[index]
    data["crypto"]["email_hmac_pepper"] = "${OSAP_AUTH_EMAIL_PEPPER}"  # type: ignore[index]
    data["crypto"]["email_aead_key_b64"] = "${OSAP_AUTH_EMAIL_AEAD_KEY}"  # type: ignore[index]
    data["crypto"]["token_hmac_pepper"] = "${OSAP_AUTH_TOKEN_PEPPER}"  # type: ignore[index]
    data["crypto"]["jwt_private_key"] = "${OSAP_AUTH_JWT_PRIVATE_KEY}"  # type: ignore[index]
    data["crypto"]["jwt_public_key"] = "${OSAP_AUTH_JWT_PUBLIC_KEY}"  # type: ignore[index]
    data["smtp"]["host"] = "${OSAP_AUTH_SMTP_HOST}"  # type: ignore[index]
    missing = set(missing_required_keys(data))
    assert {
        "database.password",
        "crypto.email_hmac_pepper",
        "crypto.email_aead_key_b64",
        "crypto.token_hmac_pepper",
        "crypto.jwt_private_key",
        "crypto.jwt_public_key",
        "smtp.host",
    }.issubset(missing)


def test_placeholders_secret_se_resuelven_desde_entorno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = {
        "OSAP_AUTH_DB_PASSWORD": "db-secret",
        "OSAP_AUTH_EMAIL_PEPPER": "email-pepper-env",
        "OSAP_AUTH_EMAIL_AEAD_KEY": "YWJjZGVmZ2hpamtsbW5vcA==",
        "OSAP_AUTH_TOKEN_PEPPER": "token-pepper-env",
        "OSAP_AUTH_JWT_PRIVATE_KEY": "private-key-env",
        "OSAP_AUTH_JWT_PUBLIC_KEY": "public-key-env",
        "OSAP_AUTH_SMTP_HOST": "smtp-env.example.test",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    data = _copy()
    data["database"]["password"] = "${OSAP_AUTH_DB_PASSWORD}"  # type: ignore[index]
    for field, name in (
        ("email_hmac_pepper", "OSAP_AUTH_EMAIL_PEPPER"),
        ("email_aead_key_b64", "OSAP_AUTH_EMAIL_AEAD_KEY"),
        ("token_hmac_pepper", "OSAP_AUTH_TOKEN_PEPPER"),
        ("jwt_private_key", "OSAP_AUTH_JWT_PRIVATE_KEY"),
        ("jwt_public_key", "OSAP_AUTH_JWT_PUBLIC_KEY"),
    ):
        data["crypto"][field] = "${" + name + "}"  # type: ignore[index]
    data["smtp"]["host"] = "${OSAP_AUTH_SMTP_HOST}"  # type: ignore[index]
    assert missing_required_keys(data) == []
    config_file = _write(tmp_path, data)
    settings = Settings(config_file=config_file)
    assert settings.database.password == values["OSAP_AUTH_DB_PASSWORD"]
    assert settings.crypto.email_hmac_pepper == values["OSAP_AUTH_EMAIL_PEPPER"]
    assert settings.crypto.email_aead_key_b64 == values["OSAP_AUTH_EMAIL_AEAD_KEY"]
    assert settings.crypto.token_hmac_pepper == values["OSAP_AUTH_TOKEN_PEPPER"]
    assert settings.smtp_host == values["OSAP_AUTH_SMTP_HOST"]
