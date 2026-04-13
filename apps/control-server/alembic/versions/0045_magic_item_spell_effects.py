"""Add reusable magic-item spell effect fields and inventory charges.

Revision ID: 0045_magic_item_spell_effects
Revises: 0044
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0045_magic_item_spell_effects"
down_revision: Union[str, None] = "0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("base_item", sa.Column("charges_max", sa.Integer(), nullable=True))
    op.add_column("base_item", sa.Column("recharge_type", sa.String(), nullable=True))
    op.add_column(
        "base_item",
        sa.Column("magic_effect_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.add_column("item", sa.Column("charges_max", sa.Integer(), nullable=True))
    op.add_column("item", sa.Column("recharge_type", sa.String(), nullable=True))
    op.add_column(
        "item",
        sa.Column("magic_effect_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.add_column("inventoryitem", sa.Column("charges_current", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("inventoryitem", "charges_current")

    op.drop_column("item", "magic_effect_json")
    op.drop_column("item", "recharge_type")
    op.drop_column("item", "charges_max")

    op.drop_column("base_item", "magic_effect_json")
    op.drop_column("base_item", "recharge_type")
    op.drop_column("base_item", "charges_max")
