"""Añade la tabla `provider_accounts` (login social upstream).

Revision ID: 0007_add_provider_accounts
Revises: 0006_add_allowed_redirect_hosts
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_add_provider_accounts"
down_revision: str | None = "0006_add_allowed_redirect_hosts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_accounts",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_sub", sa.String(255), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_sub", name="uq_provider_sub"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("provider_accounts")
