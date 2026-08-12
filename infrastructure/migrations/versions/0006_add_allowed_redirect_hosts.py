"""Añade `allowed_redirect_hosts` a `oauth_clients` (validación de redirect_uri por dominio).

Revision ID: 0006_add_allowed_redirect_hosts
Revises: 0005_add_session_client_id
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_add_allowed_redirect_hosts"
down_revision: str | None = "0005_add_session_client_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("oauth_clients", sa.Column("allowed_redirect_hosts", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("oauth_clients", "allowed_redirect_hosts")
