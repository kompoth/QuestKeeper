"""add password resets table

Revision ID: d296fa491461
Revises: 4921718b5dac
Create Date: 2026-11-17 16:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d296fa491461"
down_revision: str | Sequence[str] | None = "4921718b5dac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "password_resets",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_password_resets_expires_at"), "password_resets", ["expires_at"], unique=False)
    op.create_index(op.f("ix_password_resets_token"), "password_resets", ["token"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_password_resets_token"), table_name="password_resets")
    op.drop_index(op.f("ix_password_resets_expires_at"), table_name="password_resets")
    op.drop_table("password_resets")
