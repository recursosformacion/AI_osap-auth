"""Remitente de email falso (dev/test): registra los mensajes en memoria, no envía nada."""

from __future__ import annotations

from domain.ports.email import EmailMessage, EmailSender


class FakeEmailSender(EmailSender):
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        self.sent.append(message)
        return True
