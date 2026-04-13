"""Create tactical map catalog per campaign.

Revision ID: 0049_campaign_tactical_map_catalog
Revises: 0048_combat_map_selection
Create Date: 2026-04-04 00:00:01.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0049_campaign_tactical_map_catalog"
down_revision: Union[str, None] = "0048_combat_map_selection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_tactical_map",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("grid_width", sa.Integer(), nullable=True),
        sa.Column("grid_height", sa.Integer(), nullable=True),
        sa.Column("calibration_x", sa.Float(), nullable=True),
        sa.Column("calibration_y", sa.Float(), nullable=True),
        sa.Column("calibration_width", sa.Float(), nullable=True),
        sa.Column("calibration_height", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_campaign_tactical_map_campaign_id"),
        "campaign_tactical_map",
        ["campaign_id"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO campaign_tactical_map (
            id,
            campaign_id,
            name,
            image_url,
            grid_width,
            grid_height,
            calibration_x,
            calibration_y,
            calibration_width,
            calibration_height,
            created_at,
            updated_at
        )
        SELECT
            md5(campaign.id || '-default-map'),
            campaign.id,
            campaign.map_name,
            campaign.map_image_url,
            campaign.map_grid_width,
            campaign.map_grid_height,
            campaign.map_calibration_x,
            campaign.map_calibration_y,
            campaign.map_calibration_width,
            campaign.map_calibration_height,
            campaign.created_at,
            campaign.updated_at
        FROM campaign
        WHERE
            campaign.map_name IS NOT NULL
            OR campaign.map_image_url IS NOT NULL
            OR campaign.map_grid_width IS NOT NULL
            OR campaign.map_grid_height IS NOT NULL
            OR campaign.map_calibration_x IS NOT NULL
            OR campaign.map_calibration_y IS NOT NULL
            OR campaign.map_calibration_width IS NOT NULL
            OR campaign.map_calibration_height IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_tactical_map_campaign_id"), table_name="campaign_tactical_map")
    op.drop_table("campaign_tactical_map")
