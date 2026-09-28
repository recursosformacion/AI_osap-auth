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
    missing_required_keys,
    resolve_config_env,
    validate_startup_config,
)

_VALID: dict[str, object] = {
    "app": {"env": "production"},
    "database": {"host": "db", "name": "osap_auth", "user": "osap", "password": "secret"},
    "crypto": {"jwt_private_key": "-----BEGIN", "jwt_public_key": "-----BEGIN"},
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


def test_configuracion_valida_en_produccion_arranca(tmp_path: Path) -> None:
    validate_startup_config(_write(tmp_path, _VALID))


@pytest.mark.parametrize(
    "path",
    [
        "database.host",
        "database.name",
        "database.user",
        "database.password",
        "crypto.jwt_private_key",
        "crypto.jwt_public_key",
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
