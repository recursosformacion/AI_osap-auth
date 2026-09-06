"""Añadir audiencias permitidas a los clientes de servicio.

Revision ID: 0008_add_service_client_audiences
Revises: 0007_add_provider_accounts
Create Date: 2026-09-06

Contrato de audiencia por cliente (4D-1): `allowed_audiences` (JSON) en `service_clients`
limita las audiencias objetivo que un client puede pedir al emitir un service token.
Vacía/`NULL` = solo la audiencia global por defecto (sin override), comportamiento actual.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_add_service_client_audiences"
down_revision: str | None = "0007_add_provider_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "service_clients",
        sa.Column("allowed_audiences", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_clients", "allowed_audiences")
