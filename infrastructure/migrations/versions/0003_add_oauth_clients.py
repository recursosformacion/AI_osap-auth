"""Añade la tabla `oauth_clients` (clientes OIDC / relying parties).

Revision ID: 0003_add_oauth_clients
Revises: 0002_add_user_name
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_oauth_clients"
down_revision: str | None = "0002_add_user_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("client_id", sa.String(64), primary_key=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("redirect_uris", sa.JSON(), nullable=False),
        sa.Column("grant_types", sa.JSON(), nullable=False),
        sa.Column("response_types", sa.JSON(), nullable=False),
        sa.Column("allowed_scopes", sa.JSON(), nullable=False),
        sa.Column("pkce_required", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("token_endpoint_auth_method", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("oauth_clients")
