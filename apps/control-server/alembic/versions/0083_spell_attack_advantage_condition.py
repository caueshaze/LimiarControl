"""add attack advantage condition to spell catalogs

Revision ID: 0083_spell_attack_advantage_condition
Revises: 0082_campaign_entity_wearing_metal_armor
Create Date: 2026-05-22 17:05:00.000000
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


revision = "0083_spell_attack_advantage_condition"
down_revision = "0082_campaign_entity_wearing_metal_armor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("attack_advantage_condition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("attack_advantage_condition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "attack_advantage_condition_json")
    op.drop_column("base_spell", "attack_advantage_condition_json")
