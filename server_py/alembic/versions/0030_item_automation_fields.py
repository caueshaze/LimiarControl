"""Add structured automation fields to campaign items.

Revision ID: 0030_item_automation_fields
Revises: 0029_catalog_snapshot_lock
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0030_item_automation_fields"
down_revision: Union[str, None] = "0029_catalog_snapshot_lock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("item", sa.Column("damage_type", sa.String(), nullable=True))
    op.add_column("item", sa.Column("range_long_meters", sa.Float(), nullable=True))
    op.add_column("item", sa.Column("versatile_damage", sa.String(), nullable=True))
    op.add_column(
        "item",
        sa.Column(
            "weapon_category",
            postgresql.ENUM(
                "simple",
                "martial",
                name="baseitemweaponcategory",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "item",
        sa.Column(
            "weapon_range_type",
            postgresql.ENUM(
                "melee",
                "ranged",
                name="baseitemweaponrangetype",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "item",
        sa.Column(
            "armor_category",
            postgresql.ENUM(
                "light",
                "medium",
                "heavy",
                "shield",
                name="baseitemarmorcategory",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column("item", sa.Column("armor_class_base", sa.Integer(), nullable=True))
    op.add_column("item", sa.Column("dex_bonus_rule", sa.String(), nullable=True))
    op.add_column("item", sa.Column("strength_requirement", sa.Integer(), nullable=True))
    op.add_column("item", sa.Column("stealth_disadvantage", sa.Boolean(), nullable=True))
    op.add_column(
        "item",
        sa.Column(
            "is_shield",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE item
            SET
                damage_type = base_item.damage_type,
                range_long_meters = CASE
                    WHEN base_item.range_long IS NULL OR base_item.range_long <= 5 THEN NULL
                    ELSE GREATEST(1.0, ROUND(base_item.range_long * 0.3048))
                END,
                versatile_damage = base_item.versatile_damage,
                weapon_category = base_item.weapon_category,
                weapon_range_type = base_item.weapon_range_type,
                armor_category = base_item.armor_category,
                armor_class_base = base_item.armor_class_base,
                dex_bonus_rule = base_item.dex_bonus_rule,
                strength_requirement = base_item.strength_requirement,
                stealth_disadvantage = base_item.stealth_disadvantage,
                is_shield = COALESCE(base_item.is_shield, false)
            FROM base_item
            WHERE item.base_item_id = base_item.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET item_kind = 'weapon'
            WHERE is_custom = true
              AND item_kind IS NULL
              AND type = 'WEAPON'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET item_kind = 'armor'
            WHERE is_custom = true
              AND item_kind IS NULL
              AND type = 'ARMOR'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET item_kind = 'consumable'
            WHERE is_custom = true
              AND item_kind IS NULL
              AND type = 'CONSUMABLE'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET
                name_en_snapshot = COALESCE(name_en_snapshot, name),
                name_pt_snapshot = COALESCE(name_pt_snapshot, name)
            WHERE is_custom = true
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET stealth_disadvantage = true
            WHERE type = 'ARMOR'
              AND stealth_disadvantage IS NULL
              AND properties @> ARRAY['stealth_disadvantage']::varchar[]
            """
        )
    )


def downgrade() -> None:
    op.drop_column("item", "is_shield")
    op.drop_column("item", "stealth_disadvantage")
    op.drop_column("item", "strength_requirement")
    op.drop_column("item", "dex_bonus_rule")
    op.drop_column("item", "armor_class_base")
    op.drop_column("item", "armor_category")
    op.drop_column("item", "weapon_range_type")
    op.drop_column("item", "weapon_category")
    op.drop_column("item", "versatile_damage")
    op.drop_column("item", "range_long_meters")
    op.drop_column("item", "damage_type")
