"""Fixtures compartidos para los tests de osap-auth."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from application.context import AuthContext
from tests.fakes import (
    FakeAuditRepository,
    FakeServiceClientRepository,
    FakeSessionRepository,
    FakeTokenRepository,
    FakeUserRepository,
    make_context,
)


@pytest.fixture
def repos() -> dict[str, object]:
    return {
        "users": FakeUserRepository(),
        "sessions": FakeSessionRepository(),
        "tokens": FakeTokenRepository(),
        "clients": FakeServiceClientRepository(),
        "audit": FakeAuditRepository(),
    }


@pytest.fixture
def ctx(repos: dict[str, object]) -> AuthContext:
    c, _ = make_context(
        users=repos["users"],  # type: ignore[arg-type]
        sessions=repos["sessions"],  # type: ignore[arg-type]
        tokens=repos["tokens"],  # type: ignore[arg-type]
        clients=repos["clients"],  # type: ignore[arg-type]
        audit=repos["audit"],  # type: ignore[arg-type]
    )
    return c


@pytest.fixture
def app(ctx: AuthContext) -> TestClient:
    return TestClient(create_app(ctx))
