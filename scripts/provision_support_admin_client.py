"""Provisiona el cliente M2M dedicado de osap-api para operaciones admin de Support.

No modifica nada salvo que se indique explícitamente --apply. El secreto se muestra
una sola vez en stdout; guardarlo inmediatamente en el gestor de secretos del entorno.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from domain.entities.service_client import ServiceClient
from infrastructure.config import load_settings
from infrastructure.crypto.hmac_hasher import HmacTokenHasher
from infrastructure.crypto.secrets import SecretGenerator
from infrastructure.db.connection import create_pool
from infrastructure.repositories.sql_service_client_repository import SqlServiceClientRepository


def build_client() -> tuple[ServiceClient, str]:
    """Crea credenciales nuevas con el mínimo privilegio requerido por osap-support."""
    settings = load_settings()
    pepper = settings.crypto.token_hmac_pepper or settings.crypto.email_hmac_pepper
    if not pepper:
        raise RuntimeError(
            "Falta OSAP_AUTH_TOKEN_PEPPER (o OSAP_AUTH_EMAIL_PEPPER como fallback)"
        )

    secret = SecretGenerator().generate(32)
    client = ServiceClient.new(
        client_secret_hash=HmacTokenHasher(pepper).hash(secret),
        scopes=["support:admin"],
        allowed_audiences=["osap-support"],
    )
    return client, secret


async def provision() -> tuple[str, str]:
    settings = load_settings()
    client, secret = build_client()
    pool = await create_pool(
        host=settings.database.host,
        port=settings.database.port,
        user=settings.database.user,
        password=settings.database.password,
        db=settings.database.name,
    )
    try:
        await SqlServiceClientRepository(pool).save(client)
    finally:
        pool.close()
        await pool.wait_closed()
    return str(client.client_id), secret


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="crear el cliente en la base de datos Auth; sin esta opción no hay escrituras",
    )
    args = parser.parse_args()

    if not args.apply:
        print(
            "DRY RUN: no se ha conectado a Auth ni se ha modificado la base de datos. "
            "Revisa el alcance y vuelve a ejecutar con --apply para provisionar."
        )
        return

    client_id, secret = asyncio.run(provision())
    print(
        json.dumps(
            {
                "client_name": "osap-support-admin-service",
                "client_id": client_id,
                "client_secret": secret,
                "allowed_audiences": ["osap-support"],
                "scopes": ["support:admin"],
                "warning": (
                    "El secreto solo se muestra ahora. Guárdalo en el gestor de secretos; "
                    "no lo añadas a Git ni a logs."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
