"""Aplicación FastAPI de osap-auth."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiomysql
from fastapi import FastAPI

from api.errors import register_exception_handlers
from api.routes import auth, jwks, oauth, password_reset, system
from application.context import AuthContext
from infrastructure.config import Settings, load_settings
from infrastructure.container import build_context
from infrastructure.db.connection import create_pool

APP_VERSION = "1.0.0"


def create_app(ctx: AuthContext) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.ctx = ctx
        await ctx.begin_audit_chain()
        yield

    app = FastAPI(title="OSAP Auth", version=APP_VERSION, lifespan=lifespan)
    app.state.ctx = ctx  # disponible incluso sin ejecutar el lifespan (tests/cli)
    register_exception_handlers(app)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(password_reset.router)
    app.include_router(oauth.router)
    app.include_router(jwks.router)
    return app


def create_app_from_settings(settings: Settings | None = None) -> FastAPI:
    """Crea la app conectada a MySQL (producción)."""
    settings = settings or load_settings()
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
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(password_reset.router)
    app.include_router(oauth.router)
    app.include_router(jwks.router)
    return app


def run() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "api.main:create_app_from_settings",
        factory=True,
        host=settings.server_host,
        port=settings.server_port,
    )
