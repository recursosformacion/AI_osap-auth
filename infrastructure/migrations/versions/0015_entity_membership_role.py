"""Rol de gestión en la pertenencia a una entidad.

Revision ID: 0015_entity_membership_role
Revises: 0014_entities_email
Create Date: 2026-11-14

Aditiva. Los representantes actuales (`entities.created_by`) pasan a `manager` para
conservar su capacidad de gestión y permitir varios gestores por entidad.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_entity_membership_role"
down_revision: str | None = "0014_entities_email"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "entity_memberships",
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
    )
    op.execute(
        """
        UPDATE entity_memberships m
        JOIN entities e ON e.id = m.entity_id
        SET m.role = 'manager'
        WHERE e.created_by = m.user_id
        """
    )


def downgrade() -> None:
    op.drop_column("entity_memberships", "role")
