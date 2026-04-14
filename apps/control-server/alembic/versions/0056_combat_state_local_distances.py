"""Add local_distances JSON column to combat_state.

Stores pairwise distances (in meters) between combat participants for
non-map (theater-of-mind) combat so that LocalCombatTargetingService
can enforce weapon and spell range constraints.

Structure: {"actor_ref_id": {"target_ref_id": 5.0, ...}, ...}

Revision ID: 0056_combat_state_local_distances
Revises: 0055_combat_state_use_map
Create Date: 2026-04-14 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056_combat_state_local_distances"
down_revision: Union[str, None] = "0055_combat_state_use_map"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "local_distances",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "local_distances")
