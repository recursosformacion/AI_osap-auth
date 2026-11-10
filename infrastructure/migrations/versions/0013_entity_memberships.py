"""Pertenencia N:M usuario↔entidad con aprobación del gestor.

Revision ID: 0013_entity_memberships
Revises: 0012_users_phone
Create Date: 2026-11-08

Sustituye la pertenencia única directa (`users.entity_id`) por una tabla N:M con estado
`pending/approved/rejected`. Las pertenencias existentes se migran como `approved`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_entity_memberships"
down_revision: str | None = "0012_users_phone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entity_memberships",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("entity_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.CHAR(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "entity_id", "user_id", name="uq_entity_memberships_entity_user"
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_entity_memberships_user_status", "entity_memberships", ["user_id", "status"]
    )
    op.create_index(
        "ix_entity_memberships_entity_status", "entity_memberships", ["entity_id", "status"]
    )

    op.execute(
        """
        INSERT INTO entity_memberships
          (id, entity_id, user_id, status, requested_at, decided_at, decided_by,
           created_at, updated_at)
        SELECT UUID(), u.entity_id, u.id, 'approved', COALESCE(u.updated_at, NOW()),
               COALESCE(u.updated_at, NOW()), e.created_by, NOW(), NOW()
        FROM users u
        JOIN entities e ON e.id = u.entity_id
        WHERE u.entity_id IS NOT NULL
        """
    )

    op.drop_constraint("fk_users_entity_id", "users", type_="foreignkey")
    op.drop_column("users", "entity_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("entity_id", sa.CHAR(36), nullable=True))
    op.create_foreign_key(
        "fk_users_entity_id", "users", "entities", ["entity_id"], ["id"], ondelete="SET NULL"
    )
    op.execute(
        """
        UPDATE users u
        JOIN entity_memberships m ON m.user_id = u.id AND m.status = 'approved'
        SET u.entity_id = m.entity_id
        """
    )
    op.drop_index("ix_entity_memberships_entity_status", table_name="entity_memberships")
    op.drop_index("ix_entity_memberships_user_status", table_name="entity_memberships")
    op.drop_table("entity_memberships")
