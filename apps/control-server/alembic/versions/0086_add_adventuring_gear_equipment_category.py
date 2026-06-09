"""add adventuring_gear to baseitemequipmentcategory enum

Revision ID: 0086_add_adventuring_gear_equipment_category
Revises: 0085_spell_consumable_material_components
Create Date: 2026-06-06 00:00:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "0086_add_adventuring_gear_equipment_category"
down_revision = "0085_spell_consumable_material_components"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE baseitemequipmentcategory ADD VALUE IF NOT EXISTS 'adventuring_gear'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; a full recreate would be needed.
    pass
