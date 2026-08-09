"""Publicador de eventos que registra `user.deleted`.

En v1.0 no existe un bus de mensajería externo: el evento se registra en memoria
(observable por tests) y en el log. La integración con un broker/outbox real para
entregar `user.deleted` a osap-api se hará en una fase posterior sin cambiar el
contrato del puerto.
"""

from __future__ import annotations

import logging
import uuid

from domain.ports.event_bus import EventPublisher

logger = logging.getLogger("osap_auth.events")


class LoggingEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._events: list[dict[str, str]] = []

    @property
    def events(self) -> list[dict[str, str]]:
        return list(self._events)

    async def publish_user_deleted(self, user_id: uuid.UUID, deleted_at: str) -> None:
        event = {"user_id": str(user_id), "deleted_at": deleted_at}
        self._events.append(event)
        logger.info("event user.deleted user_id=%s", user_id)
