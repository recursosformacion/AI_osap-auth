"""Añade la columna `client_id` a `sessions` (sesiones emitidas a un RP OIDC).

Revision ID: 0005_add_session_client_id
Revises: 0004_add_authorization_codes
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_session_client_id"
down_revision: str | None = "0004_add_authorization_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("client_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "client_id")
