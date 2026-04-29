"""add declarative spell effects json columns

Revision ID: 0069_spell_declarative_effects
Revises: 0068_spell_cantrip_scaling
Create Date: 2026-04-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0069_spell_declarative_effects"
down_revision = "0068_spell_cantrip_scaling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("effects_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "base_spell",
        sa.Column("on_end_effects_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("effects_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("on_end_effects_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "on_end_effects_json")
    op.drop_column("campaign_spell", "effects_json")
    op.drop_column("base_spell", "on_end_effects_json")
    op.drop_column("base_spell", "effects_json")
