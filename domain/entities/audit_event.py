"""Evento de auditoría append-only de osap-auth."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime


class AuditEvent:
    """Evento de auditoría de seguridad. Append-only; nunca guarda secretos ni PII."""

    def __init__(
        self,
        *,
        id: uuid.UUID,
        event_type: str,
        actor: str | None,
        subject: str | None,
        ip: str | None,
        user_agent: str | None,
        outcome: str,
        context: dict[str, object],
        prev_hash: str,
        hash: str,
        timestamp: datetime | None = None,
    ) -> None:
        self.id = id
        self.event_type = event_type
        self.actor = actor
        self.subject = subject
        self.ip = ip
        self.user_agent = user_agent
        self.outcome = outcome
        self.context = context
        self.prev_hash = prev_hash
        self.hash = hash
        self.timestamp = timestamp

    @classmethod
    def new(
        cls,
        *,
        event_type: str,
        actor: str | None,
        subject: str | None,
        ip: str | None,
        user_agent: str | None,
        outcome: str,
        context: dict[str, object],
        prev_hash: str,
    ) -> AuditEvent:
        now = datetime.now(UTC)
        payload: dict[str, object] = {
            "ts": now.isoformat(),
            "event_type": event_type,
            "actor": actor,
            "subject": subject,
            "outcome": outcome,
            "context": context,
            "prev_hash": prev_hash,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return cls(
            id=uuid.uuid4(),
            event_type=event_type,
            actor=actor,
            subject=subject,
            ip=ip,
            user_agent=user_agent,
            outcome=outcome,
            context=context,
            prev_hash=prev_hash,
            hash=digest,
            timestamp=now,
        )
