"""Añade la tabla `authorization_codes` (códigos OIDC de un solo uso).

Revision ID: 0004_add_authorization_codes
Revises: 0003_add_oauth_clients
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_authorization_codes"
down_revision: str | None = "0003_add_oauth_clients"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authorization_codes",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("redirect_uri", sa.String(512), nullable=False),
        sa.Column("scope", sa.String(256), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=True),
        sa.Column("code_challenge_method", sa.String(16), nullable=True),
        sa.Column("nonce", sa.String(128), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_clients.client_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("authorization_codes")
