"""Avatar de usuario (imagen pequeña en data URL).

Revision ID: 0020_user_avatar
Revises: 0019_nickname_unique
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_user_avatar"
down_revision = "0019_nickname_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_data")
