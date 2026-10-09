"""Caso de uso: avisar por email de un cambio de reconocimiento (concedido/retirado).

El reconocimiento vive en osap-support, pero el **email del usuario es de osap-auth**
(identidad). Por eso la operación admin (osap-api) delega aquí el aviso, igual que con el
`nickname`. El envío es **best-effort**: un fallo de correo no debe romper la operación.
"""

from __future__ import annotations

import logging
import uuid

from application.context import AuthContext
from application.identity_emails import recognition_email

logger = logging.getLogger(__name__)


class NotifyRecognitionUseCase:
    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self, *, user_id: uuid.UUID, recognition_type: str, action: str, project: str
    ) -> None:
        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            logger.warning("reconocimiento: usuario %s no encontrado; sin aviso", user_id)
            return
        email = self._ctx.email_protector.decrypt(user.email_cipher) if user.email_cipher else ""
        if not email:
            logger.warning("reconocimiento: usuario %s sin email; sin aviso", user_id)
            return
        try:
            self._ctx.email_sender.send(
                recognition_email(
                    to=email,
                    recognition_type=recognition_type,
                    action=action,
                    project=project,
                    web_base_url=self._ctx.settings.web_base_url,
                )
            )
        except Exception as exc:  # noqa: BLE001 — el aviso no debe romper la operación
            logger.warning("no se pudo enviar el email de reconocimiento a %s: %s", user_id, exc)
