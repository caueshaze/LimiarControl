"""Split target_mode into target_type + area_shape on spell catalogs.

The legacy ``target_mode`` column mixed two independent concerns:
  * Targeting / delivery type: self | touch | ranged
  * Area-of-effect shape:      cone | cube | sphere | line | cylinder

This migration introduces two nullable columns — ``target_type`` and
``area_shape`` — on both ``base_spell`` and ``campaign_spell``, then
backfills them from the existing ``target_mode`` values:

    cone | cube | sphere | line | cylinder
        → target_type = 'ranged', area_shape = <shape>
    self | touch | ranged | special
        → target_type = <same>,   area_shape = NULL

Once backfilled, the legacy ``target_mode`` column is dropped — no code
reads it after this revision.

Revision ID: 0060_spell_target_type_area_shape
Revises: 0059_combat_phase_placement
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0060_spell_target_type_area_shape"
down_revision: Union[str, None] = "0059_combat_phase_placement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BACKFILL = """
    UPDATE {table}
    SET
        target_type = CASE
            WHEN target_mode IN ('cone', 'cube', 'sphere', 'line', 'cylinder') THEN 'ranged'
            WHEN target_mode IN ('self', 'touch', 'ranged', 'special') THEN target_mode
            ELSE NULL
        END,
        area_shape = CASE
            WHEN target_mode IN ('cone', 'cube', 'sphere', 'line', 'cylinder') THEN target_mode
            ELSE NULL
        END
    WHERE target_mode IS NOT NULL
"""


def upgrade() -> None:
    for table in ("base_spell", "campaign_spell"):
        op.add_column(
            table,
            sa.Column("target_type", sa.String(), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("area_shape", sa.String(), nullable=True),
        )
        op.execute(_BACKFILL.format(table=table))
        op.drop_column(table, "target_mode")


def downgrade() -> None:
    for table in ("campaign_spell", "base_spell"):
        op.add_column(
            table,
            sa.Column("target_mode", sa.String(), nullable=True),
        )
        op.execute(
            f"""
            UPDATE {table}
            SET target_mode = COALESCE(area_shape, target_type)
            """
        )
        op.drop_column(table, "area_shape")
        op.drop_column(table, "target_type")
