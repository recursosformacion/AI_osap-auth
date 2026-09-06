"""Configuración de osap-auth.

Lee secretos y ajustes de variables de entorno (pydantic-settings) y, opcionalmente,
de un fichero YAML (`config.yaml`) para valores no secretos.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OSAP_AUTH_DB_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 3306
    name: str = "osap_auth"
    user: str = "osap_auth"
    password: str = ""

    @property
    def dsn(self) -> str:
        return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_dsn(self) -> str:
        """DSN síncrono para Alembic (usa PyMySQL)."""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class CryptoConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OSAP_AUTH_", extra="ignore")

    email_hmac_pepper: str = ""
    email_aead_key_b64: str = ""
    token_hmac_pepper: str = ""
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_kid: str = "osap-auth-v1"


class RateLimitConfig:
    register_per_minute: int = 10
    login_per_minute: int = 20
    resend_verification_per_minute: int = 5
    password_reset_request_per_minute: int = 5
    password_reset_confirm_per_minute: int = 10


class Settings:
    """Configuración global del servicio."""

    def __init__(self, *, env: str = "development", config_file: Path | None = None) -> None:
        self.env = env
        self.debug = False
        self.issuer: str = "https://auth.osap"
        self.audience: str = "osap-api"
        self.access_token_ttl_seconds: int = 900
        self.refresh_token_ttl_seconds: int = 2_592_000
        self.verification_token_ttl_hours: float = 24.0
        self.password_reset_token_ttl_hours: float = 1.0
        self.key_version: int = 1
        self.audit_retention_days: int = 90
        self.allowed_token_audiences: list[str] = []
        self.rate_limit = RateLimitConfig()
        self.server_host: str = "127.0.0.1"
        self.server_port: int = 8200
        self.public_base_url: str = "http://127.0.0.1:8200"
        self.public_path_prefix: str = ""
        self.web_base_url: str = "http://127.0.0.1:5173"
        self.authorization_code_ttl_seconds: int = 300
        self.cors_origins: list[str] = []
        self.social_enabled: dict[str, bool] = {}
        self.social_credentials: dict[str, dict[str, str]] = {}
        self.social_state_secret: str = ""
        self._yaml_data: dict[str, Any] = {}

        if config_file is not None and config_file.exists():
            self._load_yaml(config_file)

        self.database = DatabaseConfig()
        self.crypto = CryptoConfig()
        self._apply_yaml(self._yaml_data)

    def _load_yaml(self, path: Path) -> None:
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        app = data.get("app", {})
        server = data.get("server", {})
        dbt = data.get("database", {})
        rl = data.get("rate_limit", {})
        self.env = app.get("env", self.env)
        self.debug = bool(app.get("debug", self.debug))
        self.issuer = data.get("issuer", self.issuer)
        self.audience = data.get("audience", self.audience)
        self.access_token_ttl_seconds = int(
            data.get("access_token_ttl_seconds", self.access_token_ttl_seconds)
        )
        self.refresh_token_ttl_seconds = int(
            data.get("refresh_token_ttl_seconds", self.refresh_token_ttl_seconds)
        )
        self.verification_token_ttl_hours = float(
            data.get("verification_token_ttl_hours", self.verification_token_ttl_hours)
        )
        self.password_reset_token_ttl_hours = float(
            data.get("password_reset_token_ttl_hours", self.password_reset_token_ttl_hours)
        )
        self.key_version = int(data.get("key_version", self.key_version))
        self.audit_retention_days = int(data.get("audit_retention_days", self.audit_retention_days))
        self.server_host = server.get("host", self.server_host)
        self.server_port = int(server.get("port", self.server_port))
        self.public_base_url = data.get("public_base_url", self.public_base_url)
        self.public_path_prefix = data.get("public_path_prefix", self.public_path_prefix)
        self.web_base_url = data.get("web_base_url", self.web_base_url)
        self.authorization_code_ttl_seconds = int(
            data.get("authorization_code_ttl_seconds", self.authorization_code_ttl_seconds)
        )
        origins = data.get("cors_origins", self.cors_origins)
        if isinstance(origins, str):
            origins = [o.strip() for o in origins.split(",") if o.strip()]
        self.cors_origins = list(origins)

        audiences = data.get("allowed_token_audiences", self.allowed_token_audiences)
        if isinstance(audiences, str):
            audiences = [a.strip() for a in audiences.split(",") if a.strip()]
        self.allowed_token_audiences = list(audiences)

        social = data.get("social", {})
        if isinstance(social, dict):
            for provider, conf in social.items():
                conf = conf or {}
                enabled = bool(conf.get("enabled", False))
                self.social_enabled[provider] = enabled
                if enabled:
                    self.social_credentials[provider] = {
                        "client_id": str(conf.get("client_id", "")),
                        "client_secret": str(conf.get("client_secret", "")),
                    }
        self.social_state_secret = data.get("social_state_secret", self.social_state_secret)

        # Guardamos la sección crypto/db para aplicarla con prioridad de YAML (dev).
        self._yaml_data = data

        # Config no secreta de DB se solapa con variables de entorno.
        if "host" in dbt:
            os.environ.setdefault("OSAP_AUTH_DB_HOST", str(dbt["host"]))
        if "port" in dbt:
            os.environ.setdefault("OSAP_AUTH_DB_PORT", str(dbt["port"]))
        if "name" in dbt:
            os.environ.setdefault("OSAP_AUTH_DB_NAME", str(dbt["name"]))
        if "user" in dbt:
            os.environ.setdefault("OSAP_AUTH_DB_USER", str(dbt["user"]))
        if "password" in dbt:
            os.environ.setdefault("OSAP_AUTH_DB_PASSWORD", str(dbt["password"]))

        for attr in (
            "register_per_minute",
            "login_per_minute",
            "resend_verification_per_minute",
            "password_reset_request_per_minute",
            "password_reset_confirm_per_minute",
        ):
            if attr in rl:
                setattr(self.rate_limit, attr, int(rl[attr]))

    def _apply_yaml(self, data: dict[str, Any]) -> None:
        """Aplica db/crypto desde YAML (dev). Los valores de YAML tienen prioridad
        solo si no vienen ya definidos en variables de entorno (secretos)."""
        dbt = data.get("database", {})
        for field, env in (
            ("host", "OSAP_AUTH_DB_HOST"),
            ("port", "OSAP_AUTH_DB_PORT"),
            ("name", "OSAP_AUTH_DB_NAME"),
            ("user", "OSAP_AUTH_DB_USER"),
            ("password", "OSAP_AUTH_DB_PASSWORD"),
        ):
            if field in dbt and not os.environ.get(env):
                setattr(self.database, field, dbt[field])

        crypto = data.get("crypto", {})
        for field, env in (
            ("email_hmac_pepper", "OSAP_AUTH_EMAIL_PEPPER"),
            ("email_aead_key_b64", "OSAP_AUTH_EMAIL_AEAD_KEY"),
            ("token_hmac_pepper", "OSAP_AUTH_TOKEN_PEPPER"),
            ("jwt_private_key", "OSAP_AUTH_JWT_PRIVATE_KEY"),
            ("jwt_public_key", "OSAP_AUTH_JWT_PUBLIC_KEY"),
        ):
            if field in crypto and not os.environ.get(env):
                setattr(self.crypto, field, crypto[field])

    def config_yaml(self) -> Path | None:
        path = PROJECT_ROOT / "config.yaml"
        return path if path.exists() else None


@lru_cache
def load_settings() -> Settings:
    settings = Settings(env=os.environ.get("OSAP_AUTH_ENV", "development"))
    yaml_path = settings.config_yaml()
    if yaml_path is not None:
        settings = Settings(config_file=yaml_path)
    return settings
