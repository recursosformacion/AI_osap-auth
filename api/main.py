"""Aplicación FastAPI de osap-auth."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiomysql
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.routes import auth, jwks, oauth, oidc, password_reset, social, system
from application.context import AuthContext
from infrastructure.config import Settings, load_settings, PROJECT_ROOT
from infrastructure.container import build_context
from infrastructure.db.connection import create_pool

APP_VERSION = "1.0.0"


def _add_middleware(app: FastAPI, cors_origins: list[str]) -> None:
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=False,
        )


def _include_routers(app: FastAPI) -> None:
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(password_reset.router)
    app.include_router(oauth.router)
    app.include_router(jwks.router)
    app.include_router(oidc.router)
    app.include_router(social.router)


def _validate_config() -> None:
    try:
        from osap.bootstrap.configuration import validate_generic_service_config
    except ImportError:
        return

    settings = load_settings()
    config_path = settings.config_yaml() or (PROJECT_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    validate_generic_service_config("osap-auth", data, config_path)


def create_app(ctx: AuthContext) -> FastAPI:
    _validate_config()
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.ctx = ctx
        await ctx.begin_audit_chain()
        yield

    app = FastAPI(title="OSAP Auth", version=APP_VERSION, lifespan=lifespan)
    app.state.ctx = ctx  # disponible incluso sin ejecutar el lifespan (tests/cli)
    register_exception_handlers(app)
    _include_routers(app)
    return app


def create_app_from_settings(settings: Settings | None = None) -> FastAPI:
    """Crea la app conectada a MySQL (producción)."""
    settings = settings or load_settings()
    _validate_config()
    pool: aiomysql.Pool | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal pool
        pool = await create_pool(
            host=settings.database.host,
            port=settings.database.port,
            user=settings.database.user,
            password=settings.database.password,
            db=settings.database.name,
        )
        app.state.ctx = build_context(settings, pool)
        await app.state.ctx.begin_audit_chain()
        yield
        if pool is not None:
            pool.close()
            await pool.wait_closed()

    app = FastAPI(title="OSAP Auth", version=APP_VERSION, lifespan=lifespan)
    register_exception_handlers(app)
    _add_middleware(app, settings.cors_origins)
    _include_routers(app)
    return app


def run() -> None:
    import uvicorn

    _validate_config()
    settings = load_settings()
    uvicorn.run(
        "api.main:create_app_from_settings",
        factory=True,
        host=settings.server_host,
        port=settings.server_port,
    )
