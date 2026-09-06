"""CLI de administración de osap-auth.

Comandos:
  migrate                    Aplica las migraciones Alembic a la BD.
  create-client --scopes=...  Crea un cliente de servicio y muestra id + secreto.
  register-oauth-client       Registra un cliente OIDC (relying party) y muestra id + secreto.
  set-admin --email=...       Promueve a admin (y verifica/activa) la cuenta por email.
  list-users                  Lista usuarios (email descifrado, roles, estado).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

import aiomysql
import yaml

from application.context import AuthContext
from domain.entities.user import UserStatus
from infrastructure.config import load_settings
from infrastructure.container import build_context
from infrastructure.db.connection import create_pool


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="osap-auth-admin")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Aplica migraciones Alembic a la BD")
    sub.add_parser("list-users", help="Lista usuarios (email descifrado, roles, estado)")

    create_client = sub.add_parser("create-client", help="Crea un cliente de servicio")
    create_client.add_argument(
        "--scopes", required=True, help="Scopes separados por coma (p.ej. storage:read)"
    )
    create_client.add_argument(
        "--audiences",
        default=None,
        help="Audiencias permitidas separadas por coma (p.ej. osap-support); "
        "vacío = solo audiencia global",
    )

    register_oauth = sub.add_parser(
        "register-oauth-client", help="Registra un cliente OIDC (relying party)"
    )
    register_oauth.add_argument(
        "--redirect-uris", required=True, help="Redirect URIs separadas por coma"
    )
    register_oauth.add_argument(
        "--allowed-hosts",
        default=None,
        help="Hosts permitidos para redirect_uri (coma). Por defecto: hosts de las redirect_uris",
    )
    register_oauth.add_argument(
        "--scopes", default="openid,profile,email", help="Scopes permitidos (coma)"
    )
    register_oauth.add_argument(
        "--grant-types", default="authorization_code,refresh_token", help="Grant types (coma)"
    )
    register_oauth.add_argument(
        "--client-id",
        default=None,
        help="client_id (UUID) fijo; si no se indica se genera uno nuevo",
    )
    register_oauth.add_argument(
        "--no-pkce", action="store_true", help="No exigir PKCE (por defecto se exige)"
    )

    set_admin = sub.add_parser("set-admin", help="Promueve a admin y verifica/activa una cuenta")
    set_admin.add_argument("--email", required=True, help="Email de la cuenta")
    return parser


async def _create_client(scopes: str, audiences: str | None = None) -> None:
    from application.use_cases.service_clients import CreateServiceClientUseCase

    settings = load_settings()
    pool = await create_pool(
        host=settings.database.host,
        port=settings.database.port,
        user=settings.database.user,
        password=settings.database.password,
        db=settings.database.name,
    )
    ctx = build_context(settings, pool)
    result = await CreateServiceClientUseCase(ctx).execute(
        scopes=[s.strip() for s in scopes.split(",") if s.strip()],
        allowed_audiences=(
            [a.strip() for a in audiences.split(",") if a.strip()] if audiences else None
        ),
    )
    print("client_id:    ", result.client_id)
    print("client_secret:", result.client_secret)
    print("GUARDA EL SECRETO: solo se muestra una vez.")
    pool.close()
    await pool.wait_closed()


async def _with_context() -> tuple[AuthContext, aiomysql.Pool]:
    settings = load_settings()
    pool = await create_pool(
        host=settings.database.host,
        port=settings.database.port,
        user=settings.database.user,
        password=settings.database.password,
        db=settings.database.name,
    )
    ctx = build_context(settings, pool)
    return ctx, pool


async def _list_users() -> None:
    ctx, pool = await _with_context()
    users = await ctx.users.list_all()
    print(f"Total usuarios: {len(users)}")
    for u in users:
        try:
            email = ctx.email_protector.decrypt(u.email_cipher) if u.email_cipher else "(sin email)"
        except Exception:
            email = "(no descifrable)"
        print(
            f"- {u.id}  {email}  name={u.name or '-'}  roles={u.roles}  "
            f"status={u.status.value}  verified={u.email_verified}"
        )
    pool.close()
    await pool.wait_closed()


async def _register_oauth_client(
    redirect_uris: str,
    allowed_hosts: str | None,
    scopes: str,
    grant_types: str,
    client_id: str | None,
    require_pkce: bool,
) -> None:
    import urllib.parse

    from domain.entities.oauth_client import OAuthClient

    ctx, pool = await _with_context()
    redirect_list = [u.strip() for u in redirect_uris.split(",") if u.strip()]
    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    grant_list = [g.strip() for g in grant_types.split(",") if g.strip()]
    if allowed_hosts is not None:
        host_list = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
    else:
        host_list = []
        for uri in redirect_list:
            host = urllib.parse.urlparse(uri).hostname
            if host and host not in host_list:
                host_list.append(host)
    raw_secret = ctx.secret_generator.generate(48)
    client = OAuthClient.new(
        client_id=client_id or f"rp-{uuid.uuid4().hex}",
        client_secret_hash=ctx.token_hasher.hash(raw_secret),
        redirect_uris=redirect_list,
        allowed_redirect_hosts=host_list,
        grant_types=grant_list,
        allowed_scopes=scope_list,
        pkce_required=require_pkce,
        token_endpoint_auth_method="client_secret_post",
    )
    await ctx.oauth_clients.save(client)
    print("client_id:    ", client.client_id)
    print("client_secret:", raw_secret)
    print("redirect_uris:", redirect_list)
    print("allowed_hosts:", host_list)
    print("GUARDA EL SECRETO: solo se muestra una vez.")
    pool.close()
    await pool.wait_closed()


async def _set_admin(email: str) -> None:
    from datetime import UTC, datetime

    ctx, pool = await _with_context()
    lookup = ctx.email_protector.lookup(email)
    user = await ctx.users.get_by_email_lookup(lookup)
    if user is None:
        print(f"No se encontró ninguna cuenta para {email}")
        pool.close()
        await pool.wait_closed()
        return
    user.roles = list(dict.fromkeys([*user.roles, "admin"]))
    user.status = UserStatus.ACTIVE
    user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    user.touch()
    await ctx.users.save(user)
    print(
        f"OK: {email} ahora es admin. roles={user.roles} status={user.status.value} "
        f"verified={user.email_verified}"
    )
    pool.close()
    await pool.wait_closed()


def main() -> None:
    try:
        from osap.bootstrap.configuration import validate_generic_service_config
    except ImportError:
        validate_generic_service_config = None  # type: ignore[assignment]

    if validate_generic_service_config is not None:
        settings = load_settings()
        fallback_config = Path(__file__).resolve().parent.parent / "config.yaml"
        config_path = settings.config_yaml() or fallback_config
        data: dict[str, object] = {}
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        validate_generic_service_config("osap-auth", data, config_path)

    args = _make_parser().parse_args()
    if args.command == "migrate":
        from infrastructure.config import load_settings as _ls

        settings = _ls()
        from infrastructure.db.migrate import run_migrations

        run_migrations(settings.database.sync_dsn)
    elif args.command == "create-client":
        asyncio.run(_create_client(args.scopes, args.audiences))
    elif args.command == "register-oauth-client":
        asyncio.run(
            _register_oauth_client(
                redirect_uris=args.redirect_uris,
                allowed_hosts=args.allowed_hosts,
                scopes=args.scopes,
                grant_types=args.grant_types,
                client_id=args.client_id,
                require_pkce=not args.no_pkce,
            )
        )
    elif args.command == "list-users":
        asyncio.run(_list_users())
    elif args.command == "set-admin":
        asyncio.run(_set_admin(args.email))
    else:
        sys.exit("comando desconocido")


if __name__ == "__main__":
    main()
