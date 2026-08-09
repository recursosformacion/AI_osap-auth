"""Rutas de sistema (health)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
