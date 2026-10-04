"""Onboarding: aceptación legal versionada + nickname, y versión legal vigente."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from application.audit import audit
from application.context import AuthContext
from application.use_cases.me import GetMeUseCase
from domain.exceptions import (
    LegalVersionOutdatedError,
    NicknameTakenError,
    UnauthorizedError,
)
from domain.services.nickname import validate as validate_nickname


class GetLegalCurrentUseCase:
    """Versión legal vigente + rutas de los documentos (recurso público)."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    def execute(self) -> dict[str, str]:
        settings = self._ctx.settings
        return {
            "terms_version": settings.terms_version,
            "privacy_version": settings.privacy_version,
            "terms_url": settings.terms_url,
            "privacy_url": settings.privacy_url,
        }


class CompleteOnboardingUseCase:
    """Completa el onboarding de forma atómica: nickname + aceptación de ToS y Privacidad."""

    def __init__(self, ctx: AuthContext) -> None:
        self._ctx = ctx

    async def execute(
        self,
        *,
        user_id: uuid.UUID,
        nickname: str,
        terms_version: str,
        privacy_version: str,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, object]:
        settings = self._ctx.settings
        if terms_version != settings.terms_version or privacy_version != settings.privacy_version:
            raise LegalVersionOutdatedError(
                "las versiones legales han cambiado; vuelve a aceptarlas"
            )
        norm = validate_nickname(nickname)

        user = await self._ctx.users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("usuario no encontrado")
        if await self._ctx.users.nickname_norm_exists(norm, exclude_user_id=user.id):
            raise NicknameTakenError("nickname no disponible")

        now = datetime.now(UTC)
        user.nickname = nickname.strip()
        user.nickname_norm = norm
        user.terms_version = settings.terms_version
        user.terms_accepted_at = now
        user.privacy_version = settings.privacy_version
        user.privacy_accepted_at = now
        if user.onboarding_completed_at is None:
            user.onboarding_completed_at = now
        user.touch()
        await self._ctx.users.save(user)

        await audit(
            self._ctx,
            event_type="onboarding.complete",
            actor=str(user.id),
            subject=str(user.id),
            ip=ip,
            user_agent=user_agent,
            outcome="success",
            context={
                "terms_version": settings.terms_version,
                "privacy_version": settings.privacy_version,
            },
        )
        return await GetMeUseCase(self._ctx).execute(user_id=user.id)
