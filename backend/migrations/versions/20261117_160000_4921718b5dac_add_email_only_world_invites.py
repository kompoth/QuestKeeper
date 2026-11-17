"""add email-only world invites

Revision ID: 4921718b5dac
Revises: 38aebedc47dc
Create Date: 2026-11-17 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4921718b5dac"
down_revision: str | Sequence[str] | None = "38aebedc47dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("world_invites", sa.Column("id", sa.String(length=36), nullable=True))
    op.execute("UPDATE world_invites SET id = UUID() WHERE id IS NULL")
    op.alter_column("world_invites", "id", existing_type=sa.String(length=36), nullable=False)

    op.drop_constraint("PRIMARY", "world_invites", type_="primary")
    op.create_primary_key("pk_world_invites", "world_invites", ["id"])
    op.create_index(op.f("ix_world_invites_world_id"), "world_invites", ["world_id"], unique=False)

    op.alter_column("world_invites", "invitee_id", existing_type=sa.String(length=36), nullable=True)
    op.create_index(op.f("ix_world_invites_invitee_id"), "world_invites", ["invitee_id"], unique=False)

    op.add_column("world_invites", sa.Column("invitee_email", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE world_invites wi JOIN users u ON wi.invitee_id = u.id "
        "SET wi.invitee_email = u.email WHERE wi.invitee_email IS NULL"
    )
    op.alter_column("world_invites", "invitee_email", existing_type=sa.String(length=255), nullable=False)
    op.create_unique_constraint(
        "uq_world_invites_world_id_invitee_email", "world_invites", ["world_id", "invitee_email"]
    )

    op.add_column("world_invites", sa.Column("confirmation_token", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_world_invites_confirmation_token", "world_invites", ["confirmation_token"])
    op.add_column("world_invites", sa.Column("token_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("world_invites", "token_expires_at")
    op.drop_constraint("uq_world_invites_confirmation_token", "world_invites", type_="unique")
    op.drop_column("world_invites", "confirmation_token")
    op.drop_constraint("uq_world_invites_world_id_invitee_email", "world_invites", type_="unique")
    op.drop_column("world_invites", "invitee_email")
    op.drop_index(op.f("ix_world_invites_invitee_id"), table_name="world_invites")
    op.alter_column("world_invites", "invitee_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_index(op.f("ix_world_invites_world_id"), table_name="world_invites")
    op.drop_constraint("pk_world_invites", "world_invites", type_="primary")
    op.create_primary_key(None, "world_invites", ["world_id", "invitee_id"])
    op.drop_column("world_invites", "id")
