"""session status and state snapshot

Revision ID: 0012_session_status_state
Revises: 0011_preferences_user
Create Date: 2026-01-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_session_status_state"
down_revision = "0011_preferences_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_enum = postgresql.ENUM("ACTIVE", "CLOSED", name="sessionstatus")
    status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "campaign_session",
        sa.Column("status", status_enum, nullable=False, server_default="CLOSED"),
    )
    op.add_column(
        "campaign_session",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign_session",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign_session",
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
    )

    op.execute(
        "UPDATE campaign_session SET status = 'ACTIVE' WHERE is_active = TRUE"
    )
    op.execute(
        "UPDATE campaign_session SET status = 'CLOSED' WHERE is_active = FALSE"
    )
    op.execute(
        "UPDATE campaign_session SET title = CONCAT('Session ', number) WHERE title IS NULL OR title = ''"
    )

    op.alter_column("campaign_session", "title", nullable=False)
    op.drop_column("campaign_session", "is_active")

    op.create_table(
        "session_state",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("player_user_id", sa.String(), nullable=False),
        sa.Column("state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_session_state_session_id",
        "session_state",
        ["session_id"],
    )
    op.create_index(
        "ix_session_state_player_user_id",
        "session_state",
        ["player_user_id"],
    )
    op.create_foreign_key(
        "session_state_session_id_fkey",
        "session_state",
        "campaign_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "session_state_player_user_id_fkey",
        "session_state",
        "app_user",
        ["player_user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("session_state_player_user_id_fkey", "session_state", type_="foreignkey")
    op.drop_constraint("session_state_session_id_fkey", "session_state", type_="foreignkey")
    op.drop_index("ix_session_state_player_user_id", table_name="session_state")
    op.drop_index("ix_session_state_session_id", table_name="session_state")
    op.drop_table("session_state")

    op.add_column(
        "campaign_session",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        "UPDATE campaign_session SET is_active = TRUE WHERE status = 'ACTIVE'"
    )
    op.execute(
        "UPDATE campaign_session SET is_active = FALSE WHERE status = 'CLOSED'"
    )
    op.drop_column("campaign_session", "duration_seconds")
    op.drop_column("campaign_session", "ended_at")
    op.drop_column("campaign_session", "started_at")
    op.drop_column("campaign_session", "status")

    status_enum = postgresql.ENUM("ACTIVE", "CLOSED", name="sessionstatus")
    status_enum.drop(op.get_bind(), checkfirst=True)
