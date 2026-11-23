"""Reconcilia el cliente M2M de osap-api para operaciones admin de Support.

El cliente es declarativo e idempotente: su UUID y secreto proceden de la configuración
del consumidor (OSAP_SUPPORT_ADMIN_CLIENT_ID / OSAP_SUPPORT_ADMIN_CLIENT_SECRET).
No escribe nada salvo con --apply y confirmación explícita de la BD de desarrollo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid

from domain.entities.service_client import ServiceClient
from infrastructure.config import load_settings
from infrastructure.crypto.hmac_hasher import HmacTokenHasher
from infrastructure.db.connection import create_pool
from infrastructure.repositories.sql_service_client_repository import SqlServiceClientRepository

CLIENT_ID_ENV = "OSAP_SUPPORT_ADMIN_CLIENT_ID"
CLIENT_SECRET_ENV = "OSAP_SUPPORT_ADMIN_CLIENT_SECRET"
EXPECTED_SCOPES = ["support:admin"]
EXPECTED_AUDIENCES = ["osap-support"]


def build_client(client_id: str, client_secret: str, pepper: str) -> ServiceClient:
    """Construye el estado deseado del cliente, sin generar identidades aleatorias."""
    if not pepper:
        raise RuntimeError("Falta OSAP_AUTH_TOKEN_PEPPER")
    try:
        parsed_id = uuid.UUID(client_id)
    except (ValueError, AttributeError) as exc:
        raise RuntimeError(f"{CLIENT_ID_ENV} debe contener un UUID válido") from exc
    if not client_secret or not client_secret.strip():
        raise RuntimeError(f"{CLIENT_SECRET_ENV} es obligatorio")

    return ServiceClient(
        client_id=parsed_id,
        client_secret_hash=HmacTokenHasher(pepper).hash(client_secret),
        scopes=EXPECTED_SCOPES.copy(),
        enabled=True,
        allowed_audiences=EXPECTED_AUDIENCES.copy(),
    )


async def provision(client_id: str, client_secret: str, expected_database: str) -> dict[str, str]:
    settings = load_settings()

    if settings.env.strip().lower() in {"prod", "production"}:
        raise RuntimeError("Bloqueado: este provisionador solo permite Auth de desarrollo")
    if settings.database.name != expected_database:
        raise RuntimeError(
            "La BD configurada no coincide con --confirm-database "
            f"(configurada={settings.database.name!r})"
        )

    pepper = settings.crypto.token_hmac_pepper
    client = build_client(client_id, client_secret, pepper)
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

    return {
        "client_id": str(client.client_id),
        "database": settings.database.name,
        "environment": settings.env,
        "scopes": ",".join(client.scopes),
        "audiences": ",".join(client.allowed_audiences),
        "result": "reconciled",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="reconciliar el cliente en Auth; sin esta opción no hay escrituras",
    )
    parser.add_argument(
        "--confirm-database",
        help="nombre exacto de la BD Auth de desarrollo; obligatorio con --apply",
    )
    args = parser.parse_args()

    if not args.apply:
        print(
            "DRY RUN: no se ha conectado a Auth ni se ha modificado la base de datos. "
            "Comprueba las variables y usa --apply --confirm-database NOMBRE_BD para aplicar."
        )
        return
    if not args.confirm_database:
        parser.error("--confirm-database es obligatorio con --apply")

    client_id = os.environ.get(CLIENT_ID_ENV, "")
    client_secret = os.environ.get(CLIENT_SECRET_ENV, "")
    result = asyncio.run(provision(client_id, client_secret, args.confirm_database))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
