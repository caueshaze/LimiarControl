"""Add obstacles_json to campaign_tactical_map.

Canonical semantic obstacle storage for campaign maps. Each row in
obstacles_json encodes a per-cell obstacle with full tactical semantics
(blocksMovement, blocksEffect, blocksVision, cover, clipsDiagonalMovement,
movementCostMultiplier). When present, this column is the authoritative
source; blocked_cells_json becomes a legacy fallback for old maps.

Revision ID: 0057_campaign_map_obstacles
Revises: 0056_combat_state_local_distances
Create Date: 2026-04-19 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0057_campaign_map_obstacles"
down_revision: Union[str, None] = "0056_combat_state_local_distances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_tactical_map",
        sa.Column("obstacles_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_tactical_map", "obstacles_json")
