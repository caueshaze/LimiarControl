"""add armor material model to base and campaign items

Revision ID: 0081_armor_material_model
Revises: 0080_user_profile_onboarding
Create Date: 2026-05-22 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0081_armor_material_model"
down_revision = "0080_user_profile_onboarding"
branch_labels = None
depends_on = None


_ARMOR_MATERIAL_ENUM = sa.Enum(
    "metal",
    "leather",
    "hide",
    "wood",
    "natural",
    "other",
    name="baseitemarmormaterial",
)


def upgrade() -> None:
    bind = op.get_bind()
    _ARMOR_MATERIAL_ENUM.create(bind, checkfirst=True)
    op.add_column("base_item", sa.Column("armor_material", _ARMOR_MATERIAL_ENUM, nullable=True))
    op.add_column("item", sa.Column("armor_material", _ARMOR_MATERIAL_ENUM, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_column("item", "armor_material")
    op.drop_column("base_item", "armor_material")
    _ARMOR_MATERIAL_ENUM.drop(bind, checkfirst=True)
