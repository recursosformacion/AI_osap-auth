"""Preferencias de noticias del usuario.

Revision ID: 0017_news_preferences
Revises: 0016_entity_access_only
Create Date: 2026-11-15

Aditiva. Guarda si el usuario quiere recibir noticias, el idioma preferido y los temas
de interés (códigos del catálogo editorial). No crea relaciones con ai_noticias: ese
módulo resuelve el perfil por `user_ref`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_news_preferences"
down_revision: str | None = "0015_entity_membership_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("news_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("news_language", sa.String(8), nullable=False, server_default="es"),
    )
    op.add_column(
        "users",
        sa.Column("news_topics_json", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("users", "news_topics_json")
    op.drop_column("users", "news_language")
    op.drop_column("users", "news_opt_in")

