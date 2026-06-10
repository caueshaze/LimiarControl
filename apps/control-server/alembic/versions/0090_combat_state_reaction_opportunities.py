"""add reaction opportunities to combat state

Revision ID: 0090_combat_state_reaction_opportunities
Revises: 0089_user_preferred_workspace_mode
Create Date: 2026-06-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0090_combat_state_reaction_opportunities"
down_revision = "0089_user_preferred_workspace_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "reaction_opportunities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "reaction_opportunities")
