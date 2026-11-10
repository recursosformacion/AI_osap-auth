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


def nickname_assigned_email(*, to: str, nickname: str) -> EmailMessage:
    body = (
        f"Te han nombrado «{nickname}» en OpenMusicRepository.\n\n"
        "Con este nombre aparecerás en la plataforma.\n"
    )
    return EmailMessage(
        to=to,
        subject=f"Te han nombrado «{nickname}»",
        body=body,
        context={"kind": "nickname_assigned", "nickname": nickname},
    )


def recognition_email(
    *, to: str, recognition_type: str, action: str, project: str
) -> EmailMessage:
    if action == "revoked":
        subject = f"Reconocimiento retirado: {recognition_type}"
        lead = (
            f"Tu reconocimiento «{recognition_type}» en {project} ha sido retirado.\n\n"
        )
    else:
        subject = f"Te han concedido un reconocimiento: {recognition_type}"
        lead = f"Te han concedido el reconocimiento «{recognition_type}» en {project}.\n\n"
    body = f"{lead}Puedes verlo en tu cuenta.\n"
    return EmailMessage(
        to=to,
        subject=subject,
        body=body,
        context={
            "kind": "recognition",
            "recognition_type": recognition_type,
            "action": action,
            "project": project,
        },
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


def membership_request_email(
    *, web_base_url: str, to: str, entity_name: str, nickname: str
) -> EmailMessage:
    link = f"{web_base_url.rstrip('/')}/auth/account/entity-requests"
    body = (
        f"«{nickname}» solicita incorporarse a la entidad «{entity_name}» en OSAP.\n\n"
        f"Revisa la solicitud y apruébala o recházala en:\n{link}\n\n"
        "Hasta que la apruebes, la persona no se considera miembro de la entidad."
    )
    return EmailMessage(
        to=to,
        subject=f"Solicitud de incorporación a {entity_name}",
        body=body,
        context={
            "kind": "membership_request",
            "entity_name": entity_name,
            "nickname": nickname,
            "link": link,
        },
    )


def membership_approved_email(
    *, web_base_url: str, to: str, entity_name: str
) -> EmailMessage:
    link = f"{web_base_url.rstrip('/')}/auth/account/entity"
    body = (
        f"Tu incorporación a la entidad «{entity_name}» ha sido aprobada.\n\n"
        f"Ya eres miembro y puedes verlo en tu cuenta:\n{link}\n"
    )
    return EmailMessage(
        to=to,
        subject=f"Incorporación aprobada: {entity_name}",
        body=body,
        context={"kind": "membership_approved", "entity_name": entity_name, "link": link},
    )


def membership_rejected_email(
    *, web_base_url: str, to: str, entity_name: str
) -> EmailMessage:
    link = f"{web_base_url.rstrip('/')}/auth/account/entity"
    body = (
        f"Tu solicitud de incorporación a la entidad «{entity_name}» ha sido rechazada.\n\n"
        f"Puedes consultar el estado en tu cuenta:\n{link}\n"
    )
    return EmailMessage(
        to=to,
        subject=f"Incorporación rechazada: {entity_name}",
        body=body,
        context={"kind": "membership_rejected", "entity_name": entity_name, "link": link},
    )
