"""Add edge_obstacles_json to campaign_tactical_map.

Revision ID: 0058_campaign_map_edge_obstacles
Revises: 0057_campaign_map_obstacles
Create Date: 2026-04-20 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0058_campaign_map_edge_obstacles"
down_revision: Union[str, None] = "0057_campaign_map_obstacles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_tactical_map",
        sa.Column("edge_obstacles_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_tactical_map", "edge_obstacles_json")
