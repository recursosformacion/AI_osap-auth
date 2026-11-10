"""Correo de contacto de la entidad agregadora.

Revision ID: 0014_entities_email
Revises: 0013_entity_memberships
Create Date: 2026-11-10

Aditiva y **sin backfill**: las entidades existentes quedan sin correo (`email` NULL).
La unicidad es por dirección en minúsculas; el envío y la verificación por enlace se
decidirán en una entrega posterior.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_entities_email"
down_revision: str | None = "0013_entity_memberships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("email", sa.String(254), nullable=True))
    op.create_unique_constraint("uq_entities_email", "entities", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_entities_email", "entities", type_="unique")
    op.drop_column("entities", "email")
