"""Add structured healing columns to base_item and item.

Revision ID: 0040_healing_consumable_columns
Revises: 0039_spell_mechanical_columns
Create Date: 2026-03-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0040_healing_consumable_columns"
down_revision: Union[str, None] = "0039_spell_mechanical_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("base_item", "item"):
        op.add_column(table, sa.Column("heal_dice", sa.String(), nullable=True))
        op.add_column(table, sa.Column("heal_bonus", sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in ("item", "base_item"):
        op.drop_column(table, "heal_bonus")
        op.drop_column(table, "heal_dice")
