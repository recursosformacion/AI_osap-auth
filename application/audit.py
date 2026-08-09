"""Helper de auditoría para casos de uso (mantiene la cadena de hashes)."""

from __future__ import annotations

from application.context import AuthContext
from domain.entities.audit_event import AuditEvent


async def audit(
    ctx: AuthContext,
    *,
    event_type: str,
    actor: str | None,
    subject: str | None,
    ip: str | None,
    user_agent: str | None,
    outcome: str,
    context: dict[str, object] | None = None,
) -> None:
    event = AuditEvent.new(
        event_type=event_type,
        actor=actor,
        subject=subject,
        ip=ip,
        user_agent=user_agent,
        outcome=outcome,
        context=context or {},
        prev_hash=ctx.audit_chain,
    )
    await ctx.audit.append(event)
    ctx.set_audit_chain(event.hash)
