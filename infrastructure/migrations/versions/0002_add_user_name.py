"""Añade el campo `name` (nombre visible) a users.

Revision ID: 0002_add_user_name
Revises: 0001_initial
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_user_name"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
