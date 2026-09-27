"""Puerto de email de osap-auth (correos transaccionales de identidad).

osap-auth envía los correos de verificación de email y recuperación de contraseña. La
implementación real es SMTP (`infrastructure/email/smtp_email_sender.py`); en dev/test se
usa un remitente falso que registra los mensajes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmailMessage:
    """Mensaje de correo ya renderizado (asunto + cuerpo en texto)."""

    to: str
    subject: str
    body: str
    context: dict[str, object] = field(default_factory=dict)


class EmailSender(ABC):
    """Frontera del proveedor de email."""

    @abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """Envía un email. Devuelve True si el servidor lo acepta; puede lanzar en fallo."""
