"""Índice único del nickname normalizado.

Revision ID: 0019_nickname_unique
Revises: 0018_news_languages
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_nickname_unique"
down_revision = "0018_news_languages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("users")}
    if "uq_users_nickname_norm" not in indexes:
        op.create_index("uq_users_nickname_norm", "users", ["nickname_norm"], unique=True)


def downgrade() -> None:
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("users")}
    if "uq_users_nickname_norm" in indexes:
        op.drop_index("uq_users_nickname_norm", table_name="users")
