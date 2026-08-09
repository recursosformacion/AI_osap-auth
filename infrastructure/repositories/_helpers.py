"""Helpers de acceso a MySQL para repositorios SQL de osap-auth."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiomysql


@asynccontextmanager
async def cursor(pool: aiomysql.Pool) -> AsyncIterator[aiomysql.DictCursor]:
    async with pool.acquire() as conn:
        cur: aiomysql.DictCursor
        async with conn.cursor(aiomysql.DictCursor) as cur:
            yield cur


async def fetch_one(
    pool: aiomysql.Pool, query: str, params: tuple[Any, ...] = ()
) -> dict[str, Any] | None:
    async with cursor(pool) as cur:
        await cur.execute(query, params)
        return await cur.fetchone()


async def fetch_all(
    pool: aiomysql.Pool, query: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    async with cursor(pool) as cur:
        await cur.execute(query, params)
        return await cur.fetchall()


async def execute(
    pool: aiomysql.Pool, query: str, params: tuple[Any, ...] = ()
) -> None:
    async with cursor(pool) as cur:
        await cur.execute(query, params)
