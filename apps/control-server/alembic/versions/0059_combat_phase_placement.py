"""Add placement phase to combat_state.

Revision ID: 0059_combat_phase_placement
Revises: 0058_campaign_map_edge_obstacles
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0059_combat_phase_placement"
down_revision: Union[str, None] = "0058_campaign_map_edge_obstacles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE combat_phase_enum ADD VALUE IF NOT EXISTS 'placement'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values directly. Keep the value available on downgrade.
    pass
