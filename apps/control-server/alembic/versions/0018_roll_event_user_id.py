"""add user_id to roll_event

Revision ID: 0018_roll_event_user_id
Revises: 0017_inventory_party_id
Create Date: 2026-03-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_roll_event_user_id"
down_revision = "0017_inventory_party_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roll_event",
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), nullable=True),
    )
    op.create_index("ix_roll_event_user_id", "roll_event", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_roll_event_user_id", table_name="roll_event")
    op.drop_column("roll_event", "user_id")
