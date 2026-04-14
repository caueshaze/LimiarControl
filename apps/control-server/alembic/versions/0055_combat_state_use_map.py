"""Add use_map flag to combat_state.

Allows the GM to opt out of tactical map integration when opening combat.
When use_map=False, all LimiarMap-dependent flows (projection, targeting,
area preview) are skipped for that combat session.

Revision ID: 0055_combat_state_use_map
Revises: 0054_spell_area_size_meters
Create Date: 2026-04-13 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0055_combat_state_use_map"
down_revision: Union[str, None] = "0054_spell_area_size_meters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "use_map",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "use_map")
