"""Add explicit area dimension columns to base_spell and campaign_spell.

Replaces the ambiguous ``area_size_meters`` column (whose meaning depends
on the area shape) with three explicit, shape-specific columns:

  - ``radius_meters``  — sphere, cylinder
  - ``length_meters``  — cone, line
  - ``side_meters``    — cube

Backfills from the existing ``area_size_meters`` value based on ``area_shape``.
The deprecated ``area_size_meters`` column is kept for one migration cycle to
allow gradual rollout; it will be dropped in a future migration.

Revision ID: 0062_spell_explicit_area_dimensions
Revises: 0061_drop_legacy_target_mode
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0062_spell_explicit_area_dimensions"
down_revision: Union[str, None] = "0061_drop_legacy_target_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("base_spell", "campaign_spell")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("radius_meters", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("length_meters", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("side_meters", sa.Integer(), nullable=True))
        op.execute(
            f"UPDATE {table} SET radius_meters = area_size_meters"
            " WHERE area_shape IN ('sphere', 'cylinder')"
        )
        op.execute(
            f"UPDATE {table} SET length_meters = area_size_meters"
            " WHERE area_shape IN ('cone', 'line')"
        )
        op.execute(
            f"UPDATE {table} SET side_meters = area_size_meters"
            " WHERE area_shape = 'cube'"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"UPDATE {table}"
            " SET area_size_meters = COALESCE(radius_meters, length_meters, side_meters)"
            " WHERE area_size_meters IS NULL"
        )
        op.drop_column(table, "side_meters")
        op.drop_column(table, "length_meters")
        op.drop_column(table, "radius_meters")
