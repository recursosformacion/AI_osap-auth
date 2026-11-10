"""Teléfono voluntario del usuario para comunicaciones por WhatsApp.

Revision ID: 0012_users_phone
Revises: 0011_users_entities
Create Date: 2026-11-08

Aditiva y **sin backfill**: el teléfono queda NULL en las cuentas existentes. No es un
identificador de cuenta: no hay unicidad ni verificación.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_users_phone"
down_revision: str | None = "0011_users_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
