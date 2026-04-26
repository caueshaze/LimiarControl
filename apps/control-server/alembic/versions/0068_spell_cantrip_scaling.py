"""add cantrip scaling to spell catalogs

Revision ID: 0068_spell_cantrip_scaling
Revises: 0067_spell_max_targets
Create Date: 2026-04-25 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0068_spell_cantrip_scaling"
down_revision = "0067_spell_max_targets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("cantrip_scaling_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("cantrip_scaling_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "cantrip_scaling_json")
    op.drop_column("base_spell", "cantrip_scaling_json")
