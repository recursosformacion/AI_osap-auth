"""Enviador de email real por SMTP (infraestructura).

No registra ni marca nada: llama al servidor SMTP y devuelve True solo si el mensaje fue
aceptado; en fallo controlado lanza :class:`EmailSendError`.

Soporta dos modos:
- **SSL implícito** (`use_ssl`, por defecto): típico de puerto 465 (`SMTP_SSL`).
- **STARTTLS** (`use_starttls`): típico de puerto 587.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as _MimeMessage

from domain.ports.email import EmailMessage, EmailSender


class EmailSendError(RuntimeError):
    """El proveedor SMTP rechazó/no pudo aceptar el mensaje."""


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int = 465
    username: str = ""
    password: str = ""
    from_address: str = ""
    use_ssl: bool = True
    use_starttls: bool = False
    timeout_seconds: float = 15.0


class SmtpEmailSender(EmailSender):
    def __init__(self, settings: SmtpSettings) -> None:
        if not settings.host or not settings.from_address:
            raise EmailSendError("SMTP host/from_address no configurados")
        self._settings = settings

    def send(self, message: EmailMessage) -> bool:
        email = _MimeMessage()
        email["From"] = self._settings.from_address
        email["To"] = message.to
        email["Subject"] = message.subject
        email.set_content(message.body)
        try:
            with self._connect() as smtp:
                smtp.ehlo()
                if self._settings.use_starttls and not self._settings.use_ssl:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if self._settings.username:
                    smtp.login(self._settings.username, self._settings.password)
                smtp.send_message(email)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailSendError(f"SMTP no aceptó el mensaje: {exc}") from exc
        return True

    def _connect(self) -> smtplib.SMTP:
        if self._settings.use_ssl:
            return smtplib.SMTP_SSL(
                self._settings.host,
                self._settings.port,
                timeout=self._settings.timeout_seconds,
                context=ssl.create_default_context(),
            )
        return smtplib.SMTP(
            self._settings.host,
            self._settings.port,
            timeout=self._settings.timeout_seconds,
        )
