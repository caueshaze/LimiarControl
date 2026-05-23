"""add requires_target_hearing to spell catalogs

Revision ID: 0083_spell_requires_target_hearing
Revises: 0082_campaign_entity_wearing_metal_armor
Create Date: 2026-05-22 21:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0083_spell_requires_target_hearing"
down_revision = "0082_campaign_entity_wearing_metal_armor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("base_spell", sa.Column("requires_target_hearing", sa.Boolean(), nullable=True))
    op.add_column("campaign_spell", sa.Column("requires_target_hearing", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_spell", "requires_target_hearing")
    op.drop_column("base_spell", "requires_target_hearing")
