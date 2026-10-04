"""Onboarding y aceptación legal versionada (nickname + ToS + privacidad).

Revision ID: 0009_users_onboarding
Revises: 0008_add_service_client_audiences
Create Date: 2026-10-02

Aditiva y **sin backfill**: las columnas quedan NULL para las cuentas existentes (no se
falsifica aceptación). El estado de onboarding se **deriva** de estos campos; `nickname_norm`
es único (admite varios NULL).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_users_onboarding"
down_revision: str | None = "0008_add_service_client_audiences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("nickname", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("nickname_norm", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("privacy_version", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_users_nickname_norm", "users", ["nickname_norm"])


def downgrade() -> None:
    op.drop_constraint("uq_users_nickname_norm", "users", type_="unique")
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "privacy_accepted_at")
    op.drop_column("users", "privacy_version")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_version")
    op.drop_column("users", "nickname_norm")
    op.drop_column("users", "nickname")
