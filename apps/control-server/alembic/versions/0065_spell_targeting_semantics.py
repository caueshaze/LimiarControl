"""Add explicit spell targeting semantics columns.

Revision ID: 0065_spell_targeting_semantics
Revises: 0064_drop_area_size_meters
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0065_spell_targeting_semantics"
down_revision: Union[str, None] = "0064_drop_area_size_meters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("base_spell", "campaign_spell")
_COLUMNS = (
    "selection_type",
    "origin_type",
    "target_anchor",
    "attack_type",
    "range_kind",
    "effect_timing",
)


def upgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            op.add_column(table, sa.Column(column, sa.String(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        for column in reversed(_COLUMNS):
            op.drop_column(table, column)
