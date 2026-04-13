"""Add campaign-level tactical map configuration.

Revision ID: 0047_campaign_map_config
Revises: 0046_base_spell_delete_set_null
Create Date: 2026-04-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0047_campaign_map_config"
down_revision: Union[str, None] = "0046_base_spell_delete_set_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaign", sa.Column("map_name", sa.String(), nullable=True))
    op.add_column("campaign", sa.Column("map_image_url", sa.String(), nullable=True))
    op.add_column("campaign", sa.Column("map_grid_width", sa.Integer(), nullable=True))
    op.add_column("campaign", sa.Column("map_grid_height", sa.Integer(), nullable=True))
    op.add_column("campaign", sa.Column("map_calibration_x", sa.Float(), nullable=True))
    op.add_column("campaign", sa.Column("map_calibration_y", sa.Float(), nullable=True))
    op.add_column("campaign", sa.Column("map_calibration_width", sa.Float(), nullable=True))
    op.add_column("campaign", sa.Column("map_calibration_height", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign", "map_calibration_height")
    op.drop_column("campaign", "map_calibration_width")
    op.drop_column("campaign", "map_calibration_y")
    op.drop_column("campaign", "map_calibration_x")
    op.drop_column("campaign", "map_grid_height")
    op.drop_column("campaign", "map_grid_width")
    op.drop_column("campaign", "map_image_url")
    op.drop_column("campaign", "map_name")
