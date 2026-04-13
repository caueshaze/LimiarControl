"""Add explicit targeting requirement flags to spell catalogs.

Revision ID: 0051_spell_targeting_requirements
Revises: 0050_campaign_tactical_map_blocked_cells
Create Date: 2026-04-04 00:00:02.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0051_spell_targeting_requirements"
down_revision: Union[str, None] = "0050_campaign_tactical_map_blocked_cells"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table_name in ("base_spell", "campaign_spell"):
        op.add_column(table_name, sa.Column("requires_target_sight", sa.Boolean(), nullable=True))
        op.add_column(table_name, sa.Column("requires_target_effect", sa.Boolean(), nullable=True))
        op.add_column(table_name, sa.Column("requires_point_sight", sa.Boolean(), nullable=True))
        op.add_column(table_name, sa.Column("requires_point_effect", sa.Boolean(), nullable=True))


def downgrade() -> None:
    for table_name in ("campaign_spell", "base_spell"):
        op.drop_column(table_name, "requires_point_effect")
        op.drop_column(table_name, "requires_point_sight")
        op.drop_column(table_name, "requires_target_effect")
        op.drop_column(table_name, "requires_target_sight")
