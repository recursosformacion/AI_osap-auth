"""CLI de administración de osap-auth.

Comandos:
  migrate                    Aplica las migraciones Alembic a la BD.
  create-client --scopes=...  Crea un cliente de servicio y muestra id + secreto.
  set-admin --email=...       Promueve a admin (y verifica/activa) la cuenta por email.
  list-users                  Lista usuarios (email descifrado, roles, estado).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import aiomysql

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

    set_admin = sub.add_parser("set-admin", help="Promueve a admin y verifica/activa una cuenta")
    set_admin.add_argument("--email", required=True, help="Email de la cuenta")
    return parser


async def _create_client(scopes: str) -> None:
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
        scopes=[s.strip() for s in scopes.split(",") if s.strip()]
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
    args = _make_parser().parse_args()
    if args.command == "migrate":
        from infrastructure.config import load_settings as _ls

        settings = _ls()
        from infrastructure.db.migrate import run_migrations

        run_migrations(settings.database.sync_dsn)
    elif args.command == "create-client":
        asyncio.run(_create_client(args.scopes))
    elif args.command == "list-users":
        asyncio.run(_list_users())
    elif args.command == "set-admin":
        asyncio.run(_set_admin(args.email))
    else:
        sys.exit("comando desconocido")


if __name__ == "__main__":
    main()
