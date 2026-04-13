"""add_session_command_event

Revision ID: 0023_session_command_event
Revises: 0022_session_runtime_state
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0023_session_command_event"
down_revision: Union[str, None] = "0022_session_runtime_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_command_event",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("campaign_session.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column(
            "member_id",
            sa.String(),
            sa.ForeignKey("campaign_member.id"),
            nullable=False,
        ),
        sa.Column("actor_name", sa.String(), nullable=True),
        sa.Column("command_type", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_command_event_session_id"),
        "session_command_event",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_command_event_user_id"),
        "session_command_event",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_command_event_member_id"),
        "session_command_event",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_command_event_command_type"),
        "session_command_event",
        ["command_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_command_event_command_type"), table_name="session_command_event")
    op.drop_index(op.f("ix_session_command_event_member_id"), table_name="session_command_event")
    op.drop_index(op.f("ix_session_command_event_user_id"), table_name="session_command_event")
    op.drop_index(op.f("ix_session_command_event_session_id"), table_name="session_command_event")
    op.drop_table("session_command_event")
