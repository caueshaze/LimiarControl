"""Drop deprecated area_size_meters column from base_spell and campaign_spell.

The ambiguous ``area_size_meters`` column has been fully replaced by explicit
shape-specific columns (radius_meters, length_meters, side_meters) since
migration 0062. The seed, frontend, and combat pipeline now use only those
fields.

Revision ID: 0064_drop_area_size_meters
Revises: 0063_spell_area_dimensions_float
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0064_drop_area_size_meters"
down_revision: Union[str, None] = "0063_spell_area_dimensions_float"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("base_spell", "campaign_spell")


def upgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "area_size_meters")


def downgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("area_size_meters", sa.Integer(), nullable=True),
        )
