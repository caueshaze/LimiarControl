"""drop campaign join code

Revision ID: 0007_drop_campaign_join_code
Revises: 0006_sessions
Create Date: 2025-01-01 01:15:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_drop_campaign_join_code"
down_revision = "0006_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_campaign_join_code", table_name="campaign")
    op.drop_column("campaign", "join_code")


def downgrade() -> None:
    op.add_column("campaign", sa.Column("join_code", sa.String(), nullable=True))
    op.create_index("ix_campaign_join_code", "campaign", ["join_code"], unique=True)
