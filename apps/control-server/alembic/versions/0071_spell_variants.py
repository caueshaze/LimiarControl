"""Add spell variants JSON to spell catalogs.

Revision ID: 0071_spell_variants
Revises: 0070_spell_persistent_areas
Create Date: 2026-04-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0071_spell_variants"
down_revision = "0070_spell_persistent_areas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("variants_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("variants_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "variants_json")
    op.drop_column("base_spell", "variants_json")
