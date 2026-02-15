"""add active session flag

Revision ID: 0009_active_session
Revises: 0008_auth
Create Date: 2026-01-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_active_session"
down_revision = "0008_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign_session",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE campaign_session AS cs
        SET is_active = TRUE
        FROM (
            SELECT campaign_id, MAX(created_at) AS max_created
            FROM campaign_session
            GROUP BY campaign_id
        ) AS latest
        WHERE cs.campaign_id = latest.campaign_id
          AND cs.created_at = latest.max_created
        """
    )
    op.alter_column("campaign_session", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("campaign_session", "is_active")
