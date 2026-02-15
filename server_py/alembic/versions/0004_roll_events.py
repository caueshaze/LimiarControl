"""roll events

Revision ID: 0004_roll_events
Revises: 0003_preferences
Create Date: 2025-01-01 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_roll_events"
down_revision = "0003_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_mode_enum = postgresql.ENUM(
        "GM", "PLAYER", name="rolemode", create_type=False
    )
    op.create_table(
        "roll_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("author_name", sa.String(), nullable=False),
        sa.Column(
            "role_mode",
            role_mode_enum,
            nullable=False,
        ),
        sa.Column("label", sa.String()),
        sa.Column("expression", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("sides", sa.Integer(), nullable=False),
        sa.Column("modifier", sa.Integer(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_roll_event_campaign_id", "roll_event", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_roll_event_campaign_id", table_name="roll_event")
    op.drop_table("roll_event")
