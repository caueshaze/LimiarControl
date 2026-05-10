"""add combat game-time accounting fields

Revision ID: 0076_combat_game_time_accounting
Revises: 0075_game_time_seconds
Create Date: 2026-05-10 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0076_combat_game_time_accounting"
down_revision = "0075_game_time_seconds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "active_started_at_game_time_seconds",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.add_column(
        "combat_state",
        sa.Column(
            "accounted_game_time_rounds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "accounted_game_time_rounds")
    op.drop_column("combat_state", "active_started_at_game_time_seconds")
