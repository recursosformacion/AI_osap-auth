"""Autorización pública del nickname (consentimiento de cuenta, independiente de ToS/privacidad).

Revision ID: 0010_users_nickname_public_consent
Revises: 0009_users_onboarding
Create Date: 2026-10-03

Aditiva y **sin backfill**: por defecto `0` (no autorizado). No se mezcla con la aceptación
de Términos/Privacidad ni con el consentimiento por reconocimiento.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_users_public_consent"
down_revision: str | None = "0009_users_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "nickname_public_consent", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "users", sa.Column("nickname_public_consent_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "nickname_public_consent_at")
    op.drop_column("users", "nickname_public_consent")
