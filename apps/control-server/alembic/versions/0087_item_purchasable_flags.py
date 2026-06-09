"""add purchasable flags to base_item and item

Revision ID: 0087_item_purchasable_flags
Revises: 0086_add_adventuring_gear_equipment_category
Create Date: 2026-06-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0087_item_purchasable_flags"
down_revision = "0086_add_adventuring_gear_equipment_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_item",
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "item",
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("item", "is_purchasable")
    op.drop_column("base_item", "is_purchasable")
