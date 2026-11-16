"""Idiomas múltiples para noticias.

Revision ID: 0018_news_languages
Revises: 0017_news_preferences
Create Date: 2026-11-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_news_languages"
down_revision: str | None = "0017_news_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "news_languages_json",
            sa.Text(),
            nullable=False,
            server_default='["es"]',
        ),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, news_language FROM users")).fetchall()
    for user_id, language in rows:
        bind.execute(
            sa.text("UPDATE users SET news_languages_json = :value WHERE id = :id"),
            {"value": f'["{language or "es"}"]', "id": user_id},
        )


def downgrade() -> None:
    op.drop_column("users", "news_languages_json")
