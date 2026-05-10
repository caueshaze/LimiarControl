"""add spell anchors to combat state

Revision ID: 0074_spell_anchors
Revises: 0073_merge_spell_catalog_heads
Create Date: 2026-05-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0074_spell_anchors"
down_revision = "0073_merge_spell_catalog_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "spell_anchors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "spell_anchors")
