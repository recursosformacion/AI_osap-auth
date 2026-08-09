"""Ejecuta las migraciones Alembic de osap-auth."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _alembic_config(dsn: str) -> Config:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "infrastructure" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", dsn)
    return cfg


def run_migrations(sync_dsn: str) -> None:
    command.upgrade(_alembic_config(sync_dsn), "head")


if __name__ == "__main__":
    run_migrations(os.environ["OSAP_AUTH_SYNC_DSN"])
