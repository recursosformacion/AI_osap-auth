"""Mensajes de correo de identidad de osap-auth (verificación y recuperación)."""

from __future__ import annotations

from domain.ports.email import EmailMessage


def _auth_link(web_base_url: str, path: str, token: str) -> str:
    return f"{web_base_url.rstrip('/')}{path}?token={token}"


def verification_email(
    *, web_base_url: str, to: str, token: str, ttl_hours: float
) -> EmailMessage:
    link = _auth_link(web_base_url, "/auth/verify-email", token)
    body = (
        "Confirma tu dirección de email para activar tu cuenta de OSAP.\n\n"
        f"Abre este enlace (caduca en {int(ttl_hours)} h):\n{link}\n\n"
        "Si no has creado una cuenta, ignora este mensaje."
    )
    return EmailMessage(
        to=to,
        subject="Verifica tu email en OSAP",
        body=body,
        context={"kind": "verify_email", "link": link},
    )


def password_reset_email(
    *, web_base_url: str, to: str, token: str, ttl_hours: float
) -> EmailMessage:
    link = _auth_link(web_base_url, "/auth/reset-password", token)
    body = (
        "Hemos recibido una petición para restablecer tu contraseña de OSAP.\n\n"
        f"Abre este enlace (caduca en {ttl_hours:g} h):\n{link}\n\n"
        "Si no lo has solicitado, ignora este mensaje."
    )
    return EmailMessage(
        to=to,
        subject="Restablece tu contraseña de OSAP",
        body=body,
        context={"kind": "reset_password", "link": link},
    )
