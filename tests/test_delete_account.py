"""Tests de borrado de cuenta y auditoría."""

# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from application.use_cases.delete_account import DeleteAccountUseCase
from application.use_cases.login import LoginUseCase
from application.use_cases.register import RegisterUseCase
from domain.exceptions import InvalidCredentialsError
from tests.fakes import make_context


async def test_delete_account_emits_user_deleted_and_anonymizes() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    await LoginUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001

    await DeleteAccountUseCase(ctx).execute(user_id=user.id, ip=None, user_agent=None)

    # Estado borrado, credencial y email recuperable eliminados.
    assert user.status.value == "deleted"
    assert user.password_hash == ""
    assert user.email_cipher == b""
    # No resuelve por el email original.
    assert await ctx.users.get_by_email_lookup(ctx.email_protector.lookup("u@example.com")) is None

    # Evento user.deleted publicado para osap-api.
    events = ctx.events.events  # type: ignore[attr-defined]
    assert any(e["user_id"] == str(user.id) for e in events)

    # Auditoría registró el borrado.
    assert any(e.event_type == "user.deleted" for e in ctx.audit.events)  # type: ignore[attr-defined]


async def test_audit_events_recorded_on_login_failure() -> None:
    ctx, _ = make_context()
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password="s3cret-password", ip=None, user_agent=None
    )
    from application.use_cases.login import LoginUseCase as _L

    try:
        await _L(ctx).execute(
            email="u@example.com", password="wrong-password", ip=None, user_agent=None
        )
    except InvalidCredentialsError:
        pass
    types = [e.event_type for e in ctx.audit.events]  # type: ignore[attr-defined]
    assert "login.failed" in types
