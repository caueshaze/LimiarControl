"""add pending spell casts to combat state

Revision ID: 0091_combat_state_pending_spell_casts
Revises: 0090_combat_state_reaction_opportunities
Create Date: 2026-06-09 00:00:00.000001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0091_combat_state_pending_spell_casts"
down_revision = "0090_combat_state_reaction_opportunities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "pending_spell_casts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "pending_spell_casts")
