"""add wearing_metal_armor to campaign entity

Revision ID: 0082_campaign_entity_wearing_metal_armor
Revises: 0081_armor_material_model
Create Date: 2026-05-22 16:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0082_campaign_entity_wearing_metal_armor"
down_revision = "0081_armor_material_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaign_entity", sa.Column("wearing_metal_armor", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_entity", "wearing_metal_armor")
