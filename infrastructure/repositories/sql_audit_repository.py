"""Repositorio SQL de auditoría append-only de osap-auth."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import aiomysql

from domain.entities.audit_event import AuditEvent
from domain.ports.audit_repository import AuditRepository
from infrastructure.repositories._helpers import cursor


def _from_row(row: dict[str, Any]) -> AuditEvent:
    return AuditEvent(
        id=uuid.UUID(row["id"]),
        event_type=row["event_type"],
        actor=row["actor"],
        subject=row["subject"],
        ip=row["ip"],
        user_agent=row["user_agent"],
        outcome=row["outcome"],
        context=json.loads(row["context"]) if isinstance(row["context"], str) else row["context"],
        prev_hash=row["prev_hash"],
        hash=row["hash"],
        timestamp=row["timestamp"],
    )


class SqlAuditRepository(AuditRepository):
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    async def append(self, event: AuditEvent) -> None:
        context = json.dumps(event.context, default=str)
        async with cursor(self._pool) as cur:
            await cur.execute(
                """
                INSERT INTO audit_events
                  (id, event_type, actor, subject, ip, user_agent, outcome, context,
                   prev_hash, hash, timestamp)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(event.id),
                    event.event_type,
                    event.actor,
                    event.subject,
                    event.ip,
                    event.user_agent,
                    event.outcome,
                    context,
                    event.prev_hash,
                    event.hash,
                    event.timestamp,
                ),
            )

    async def last_hash(self) -> str:
        async with cursor(self._pool) as cur:
            await cur.execute(
                "SELECT hash FROM audit_events ORDER BY timestamp DESC, id DESC LIMIT 1"
            )
            row = await cur.fetchone()
        return row["hash"] if row else ""

    async def purge_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        async with cursor(self._pool) as cur:
            await cur.execute("DELETE FROM audit_events WHERE timestamp < %s", (cutoff,))
            return cur.rowcount
