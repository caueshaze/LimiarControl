"""Change radius_meters, length_meters, side_meters from INTEGER to FLOAT.

D&D 5e area sizes frequently land on multiples of 1.5 m (1 cell):
  15 ft = 4.572 m → stored as 4.5 m → meters_to_cells(4.5) = 3  ✓
  10 ft = 3.048 m → stored as 3.0 m → meters_to_cells(3.0)  = 2  ✓

Integer columns forced rounding at the storage layer (4 instead of 4.5),
producing off-by-one cell counts for 15 ft spells (Burning Hands, Thunderwave).
FLOAT preserves the intent and keeps meter_to_cells arithmetic clean.

area_size_meters is deprecated and stays INTEGER (not worth migrating).

Revision ID: 0063_spell_area_dimensions_float
Revises: 0062_spell_explicit_area_dimensions
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0063_spell_area_dimensions_float"
down_revision: Union[str, None] = "0062_spell_explicit_area_dimensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("base_spell", "campaign_spell")
_COLS = ("radius_meters", "length_meters", "side_meters")


def upgrade() -> None:
    for table in _TABLES:
        for col in _COLS:
            op.alter_column(
                table,
                col,
                type_=sa.Float(),
                existing_type=sa.Integer(),
                existing_nullable=True,
            )


def downgrade() -> None:
    for table in _TABLES:
        for col in _COLS:
            op.alter_column(
                table,
                col,
                type_=sa.Integer(),
                existing_type=sa.Float(),
                existing_nullable=True,
            )
