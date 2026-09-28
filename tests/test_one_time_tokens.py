"""Tests de A6b: consumo atómico de tokens de un solo uso y códigos de autorización.

Se cubre el patrón `get_by_hash -> is_used -> consume` con CAS y, sobre todo, doble uso
concurrente real (barrera que fuerza dos lecturas antes de consumir).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from application.use_cases.oidc_token import ExchangeAuthorizationCodeUseCase, TokenResult
from application.use_cases.password_reset import ConfirmPasswordResetUseCase
from application.use_cases.register import RegisterUseCase
from application.use_cases.verify_email import VerifyEmailUseCase
from domain.entities.authorization_code import AuthorizationCode
from domain.entities.oauth_client import OAuthClient
from domain.entities.token_record import TokenPurpose, TokenRecord
from domain.exceptions import InvalidTokenError, OAuthError
from domain.util import pkce_challenge
from tests.fakes import (
    FakeAuthorizationCodeRepository,
    FakeTokenRepository,
    make_context,
)

_PASSWORD = "s3cret-password"


def _new_token(ctx, purpose: TokenPurpose, raw: str, user_id: uuid.UUID) -> TokenRecord:
    token = TokenRecord.new(
        user_id=user_id,
        purpose=purpose,
        token_hash=ctx.token_hasher.hash(raw),
        ttl_hours=1,
    )
    token.expires_at = datetime.now(UTC) + timedelta(minutes=30)
    return token


async def test_token_consume_es_atomico() -> None:
    ctx, _ = make_context()
    token = _new_token(ctx, TokenPurpose.VERIFY_EMAIL, "raw", uuid.uuid4())
    await ctx.tokens.save(token)
    assert await ctx.tokens.consume(token.id) is True
    assert await ctx.tokens.consume(token.id) is False


async def test_authorization_code_consume_es_atomico() -> None:
    ctx, _ = make_context()
    code = AuthorizationCode(
        id=uuid.uuid4(),
        client_id="client",
        user_id=uuid.uuid4(),
        redirect_uri="https://rp/cb",
        scope="openid",
        code_hash="hash",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    await ctx.authorization_codes.save(code)
    assert await ctx.authorization_codes.consume(code.id) is True
    assert await ctx.authorization_codes.consume(code.id) is False


class _BarrierTokenRepository(FakeTokenRepository):
    def __init__(self) -> None:
        super().__init__()
        self._readers = 0
        self._both_read = asyncio.Event()

    async def get_by_hash(self, token_hash: str, purpose: TokenPurpose) -> TokenRecord | None:
        record = await super().get_by_hash(token_hash, purpose)
        if record is not None:
            self._readers += 1
            if self._readers >= 2:
                self._both_read.set()
            await self._both_read.wait()
        return record


class _BarrierCodeRepository(FakeAuthorizationCodeRepository):
    def __init__(self) -> None:
        super().__init__()
        self._readers = 0
        self._both_read = asyncio.Event()

    async def get_by_hash(self, code_hash: str) -> AuthorizationCode | None:
        record = await super().get_by_hash(code_hash)
        if record is not None:
            self._readers += 1
            if self._readers >= 2:
                self._both_read.set()
            await self._both_read.wait()
        return record


async def test_verify_email_doble_uso_concurrente_solo_uno_gana() -> None:
    ctx, _ = make_context(tokens=_BarrierTokenRepository())
    result = await RegisterUseCase(ctx).execute(
        email="u@example.com", password=_PASSWORD, ip=None, user_agent=None
    )
    raw = result.verification_token
    assert raw

    results = await asyncio.gather(
        VerifyEmailUseCase(ctx).execute(token=raw, ip=None, user_agent=None),
        VerifyEmailUseCase(ctx).execute(token=raw, ip=None, user_agent=None),
        return_exceptions=True,
    )
    errs = [r for r in results if isinstance(r, BaseException)]
    assert len(errs) == 1
    assert isinstance(errs[0], InvalidTokenError)
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    assert user.email_verified is True


async def test_password_reset_doble_uso_concurrente_solo_uno_gana() -> None:
    ctx, _ = make_context(tokens=_BarrierTokenRepository())
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password=_PASSWORD, ip=None, user_agent=None
    )
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    raw = "raw-reset-token"
    await ctx.tokens.save(_new_token(ctx, TokenPurpose.RESET_PASSWORD, raw, user.id))

    results = await asyncio.gather(
        ConfirmPasswordResetUseCase(ctx).execute(
            token=raw, new_password="new-s3cret-password", ip=None, user_agent=None
        ),
        ConfirmPasswordResetUseCase(ctx).execute(
            token=raw, new_password="new-s3cret-password", ip=None, user_agent=None
        ),
        return_exceptions=True,
    )
    errs = [r for r in results if isinstance(r, BaseException)]
    assert len(errs) == 1
    assert isinstance(errs[0], InvalidTokenError)


async def test_authorization_code_doble_canje_concurrente_solo_uno_gana() -> None:
    ctx, _ = make_context(authorization_codes=_BarrierCodeRepository())
    await RegisterUseCase(ctx).execute(
        email="u@example.com", password=_PASSWORD, ip=None, user_agent=None
    )
    user = next(iter(ctx.users._users.values()))  # noqa: SLF001
    registered = await ctx.users.get_by_id(user.id)
    assert registered is not None

    client = OAuthClient.new(
        client_id="rp-client",
        client_secret_hash=ctx.token_hasher.hash("rp-secret"),
        redirect_uris=["https://rp/cb"],
        pkce_required=True,
        token_endpoint_auth_method="client_secret_post",
    )
    await ctx.oauth_clients.save(client)

    verifier = "verifier-value"
    raw_code = "raw-auth-code"
    code = AuthorizationCode(
        id=uuid.uuid4(),
        client_id="rp-client",
        user_id=registered.id,
        redirect_uri="https://rp/cb",
        scope="openid profile",
        code_hash=ctx.token_hasher.hash(raw_code),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        code_challenge=pkce_challenge(verifier),
        code_challenge_method="S256",
    )
    await ctx.authorization_codes.save(code)

    async def _exchange() -> TokenResult:
        return await ExchangeAuthorizationCodeUseCase(ctx).execute(
            code=raw_code,
            code_verifier=verifier,
            redirect_uri="https://rp/cb",
            client_id="rp-client",
            client_secret="rp-secret",
            ip=None,
            user_agent=None,
        )

    results = await asyncio.gather(_exchange(), _exchange(), return_exceptions=True)
    ok = [r for r in results if not isinstance(r, BaseException)]
    errs = [r for r in results if isinstance(r, BaseException)]
    assert len(ok) == 1
    assert len(errs) == 1
    assert isinstance(errs[0], OAuthError)
