"""Conexión a MySQL (aiomysql) de osap-auth. Solo desde `infrastructure`."""

from __future__ import annotations

import aiomysql
from aiomysql import Pool


async def create_pool(*, host: str, port: int, user: str, password: str, db: str) -> Pool:
    return await aiomysql.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db,
        autocommit=True,
        minsize=1,
        maxsize=10,
        charset="utf8mb4",
    )
