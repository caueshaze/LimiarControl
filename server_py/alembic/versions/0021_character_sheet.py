"""add_character_sheet

Revision ID: 0021_character_sheet
Revises: 0020_lobby_session_status
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_character_sheet"
down_revision: Union[str, None] = "0020_lobby_session_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "character_sheet",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "party_id",
            sa.String(),
            sa.ForeignKey("party.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_user_id",
            sa.String(),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_character_sheet_party_id", "character_sheet", ["party_id"])
    op.create_index(
        "ix_character_sheet_player_user_id", "character_sheet", ["player_user_id"]
    )
    op.create_unique_constraint(
        "uq_character_sheet_party_player",
        "character_sheet",
        ["party_id", "player_user_id"],
    )


def downgrade() -> None:
    op.drop_table("character_sheet")
