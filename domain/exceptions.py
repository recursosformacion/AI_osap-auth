"""Excepciones de dominio de osap-auth.

Todas son respondidas por la capa API con el código HTTP correspondiente.
Nunca deben filtrar datos internos (emails, hashes, tokens) en su mensaje.
"""

from __future__ import annotations


class DomainError(Exception):
    """Error base de dominio."""

    status_code = 400


class InvalidCredentialsError(DomainError):
    """Email/contraseña no válidos. Respuesta genérica anti-enumeración."""

    status_code = 401


class AccountDisabledError(DomainError):
    """La cuenta está deshabilitada."""

    status_code = 403


class EmailNotVerifiedError(DomainError):
    """Operación que exige email verificado."""

    status_code = 403


class EmailAlreadyVerifiedError(DomainError):
    """El email ya estaba verificado."""

    status_code = 409


class EmailTakenError(DomainError):
    """El email ya está en uso. (El contrato exige respuesta genérica en registro.)"""

    status_code = 409


class InvalidTokenError(DomainError):
    """Token ausente, malformado, caducado o ya usado."""

    status_code = 401


class TokenExpiredError(InvalidTokenError):
    """Token caducado."""

    status_code = 401


class TokenReuseDetectedError(DomainError):
    """Reutilización de un token de un solo uso o de un refresh ya rotado."""

    status_code = 401


class SessionNotFoundError(DomainError):
    """La sesión indicada no existe o no pertenece al usuario."""

    status_code = 404


class UserNotFoundError(DomainError):
    """El usuario indicado no existe o está eliminado."""

    status_code = 404


class UnauthorizedError(DomainError):
    """Falta credencial de usuario o token de servicio válido."""

    status_code = 401


class ForbiddenError(DomainError):
    """Credencial válida pero sin autorización."""

    status_code = 403


class PasswordPolicyError(DomainError):
    """La contraseña no cumple la política."""

    status_code = 422


class WeakPasswordError(PasswordPolicyError):
    """Contraseña demasiado corta o sin la complejidad mínima."""

    status_code = 422


class InvalidEmailError(DomainError):
    """Email malformado."""

    status_code = 422


class ServiceClientNotFoundError(DomainError):
    """Client_id o client_secret de servicio inválidos."""

    status_code = 401


class ServiceClientDisabledError(DomainError):
    """Cliente de servicio deshabilitado."""

    status_code = 403


class RateLimitedError(DomainError):
    """Se ha superado el límite de peticiones."""

    status_code = 429
