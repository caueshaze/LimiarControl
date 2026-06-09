"""add magic_bracelet category and item equipment_category

Revision ID: 0088_magic_bracelet_category_and_item_equipment_category
Revises: 0087_item_purchasable_flags
Create Date: 2026-06-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0088_magic_bracelet_category_and_item_equipment_category"
down_revision = "0087_item_purchasable_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE baseitemequipmentcategory ADD VALUE IF NOT EXISTS 'magic_bracelet'")
    op.add_column(
        "item",
        sa.Column(
            "equipment_category",
            sa.Enum(name="baseitemequipmentcategory", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("item", "equipment_category")
