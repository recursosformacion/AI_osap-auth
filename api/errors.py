"""Errores HTTP y su manejo en la API de osap-auth."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.exceptions import (
    AccountDisabledError,
    DomainError,
    EmailAlreadyVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitedError,
    SessionNotFoundError,
    TokenReuseDetectedError,
    UnauthorizedError,
)

_KNOWN: dict[type[DomainError], int] = {
    InvalidCredentialsError: 401,
    InvalidTokenError: 401,
    TokenReuseDetectedError: 401,
    UnauthorizedError: 401,
    AccountDisabledError: 403,
    EmailAlreadyVerifiedError: 409,
    SessionNotFoundError: 404,
    RateLimitedError: 429,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        status = _KNOWN.get(type(exc), exc.status_code)
        return JSONResponse(status_code=status, content={"detail": str(exc)})
