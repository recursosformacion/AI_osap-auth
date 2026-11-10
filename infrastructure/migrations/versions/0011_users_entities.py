"""Entidades agregadoras de usuarios (coral, orquesta, grupo).

Revision ID: 0011_users_entities
Revises: 0010_users_public_consent
Create Date: 2026-11-08

Aditiva y **sin backfill**: los usuarios existentes quedan sin entidad (`entity_id` NULL).
`entities.name_norm` es único (comparación case-insensitive). El usuario que crea una
entidad queda como su representante (`created_by`) y se le asigna como miembro.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_users_entities"
down_revision: str | None = "0010_users_public_consent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_norm", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name_norm", name="uq_entities_name_norm"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.add_column("users", sa.Column("entity_id", sa.CHAR(36), nullable=True))
    op.create_foreign_key(
        "fk_users_entity_id", "users", "entities", ["entity_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_entity_id", "users", type_="foreignkey")
    op.drop_column("users", "entity_id")
    op.drop_table("entities")
