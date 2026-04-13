"""add purchase_event table

Revision ID: 0019_purchase_event
Revises: 0018_roll_event_user_id
Create Date: 2026-03-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_purchase_event"
down_revision = "0018_roll_event_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("campaign_session.id"), nullable=False, index=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), nullable=True, index=True),
        sa.Column("member_id", sa.String(), sa.ForeignKey("campaign_member.id"), nullable=False, index=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("item.id"), nullable=False, index=True),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("purchase_event")
