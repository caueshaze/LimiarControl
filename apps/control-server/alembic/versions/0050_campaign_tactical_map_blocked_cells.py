"""Add blocked_cells_json to campaign_tactical_map.

Phase 1 of tactical obstacle handling: store movement-blocking cells
alongside the map definition so they survive session restarts and are
sent to LimiarMap when combat starts.

Revision ID: 0050_campaign_tactical_map_blocked_cells
Revises: 0049_campaign_tactical_map_catalog
Create Date: 2026-04-04 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0050_campaign_tactical_map_blocked_cells"
down_revision: Union[str, None] = "0049_campaign_tactical_map_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_tactical_map",
        sa.Column("blocked_cells_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_tactical_map", "blocked_cells_json")
