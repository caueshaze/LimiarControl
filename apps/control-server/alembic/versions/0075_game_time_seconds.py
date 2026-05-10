"""add game_time_seconds to session_runtime

Revision ID: 0075_game_time_seconds
Revises: 0074_spell_anchors
Create Date: 2026-05-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0075_game_time_seconds"
down_revision = "0074_spell_anchors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "session_runtime",
        sa.Column(
            "game_time_seconds",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("session_runtime", "game_time_seconds")
