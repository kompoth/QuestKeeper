"""add pending registrations table

Revision ID: c21894b0cfd0
Revises: d296fa491461
Create Date: 2026-11-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c21894b0cfd0"
down_revision: str | Sequence[str] | None = "d296fa491461"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pending_registrations",
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(op.f("ix_pending_registrations_email"), "pending_registrations", ["email"], unique=True)
    op.create_index(op.f("ix_pending_registrations_expires_at"), "pending_registrations", ["expires_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_pending_registrations_expires_at"), table_name="pending_registrations")
    op.drop_index(op.f("ix_pending_registrations_email"), table_name="pending_registrations")
    op.drop_table("pending_registrations")
