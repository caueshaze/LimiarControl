"""Add structured mechanical columns to base_spell and campaign_spell.

New columns: casting_time_type, target_mode, resolution_type,
damage_dice, heal_dice, upcast_mode, upcast_value.

Revision ID: 0039_spell_mechanical_columns
Revises: 0038_metric_catalog_ranges
Create Date: 2026-03-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0039_spell_mechanical_columns"
down_revision: Union[str, None] = "0038_metric_catalog_ranges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("base_spell", "campaign_spell"):
        op.add_column(table, sa.Column("casting_time_type", sa.String(), nullable=True))
        op.add_column(table, sa.Column("target_mode", sa.String(), nullable=True))
        op.add_column(table, sa.Column("resolution_type", sa.String(), nullable=True))
        op.add_column(table, sa.Column("damage_dice", sa.String(), nullable=True))
        op.add_column(table, sa.Column("heal_dice", sa.String(), nullable=True))
        op.add_column(table, sa.Column("upcast_mode", sa.String(), nullable=True))
        op.add_column(table, sa.Column("upcast_value", sa.String(), nullable=True))


def downgrade() -> None:
    for table in ("campaign_spell", "base_spell"):
        op.drop_column(table, "upcast_value")
        op.drop_column(table, "upcast_mode")
        op.drop_column(table, "heal_dice")
        op.drop_column(table, "damage_dice")
        op.drop_column(table, "resolution_type")
        op.drop_column(table, "target_mode")
        op.drop_column(table, "casting_time_type")
