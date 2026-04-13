"""Harden base item mechanical fields with enums.

Revision ID: 0036_harden_base_item_mechanics
Revises: 0035_system_admin_base_items
Create Date: 2026-03-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0036_harden_base_item_mechanics"
down_revision: Union[str, None] = "0035_system_admin_base_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_legacy_values() -> None:
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET equipment_category = LOWER(TRIM(equipment_category))
            WHERE equipment_category IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET damage_type = LOWER(TRIM(damage_type))
            WHERE damage_type IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET damage_type = LOWER(TRIM(damage_type))
            WHERE damage_type IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET dex_bonus_rule = CASE LOWER(TRIM(dex_bonus_rule))
                WHEN '0' THEN 'none'
                WHEN 'max_0' THEN 'none'
                WHEN 'max 0' THEN 'none'
                WHEN 'none' THEN 'none'
                WHEN 'full' THEN 'full'
                WHEN 'unlimited' THEN 'full'
                WHEN 'max_2' THEN 'max_2'
                WHEN 'max 2' THEN 'max_2'
                ELSE LOWER(TRIM(dex_bonus_rule))
            END
            WHERE dex_bonus_rule IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE item
            SET dex_bonus_rule = CASE LOWER(TRIM(dex_bonus_rule))
                WHEN '0' THEN 'none'
                WHEN 'max_0' THEN 'none'
                WHEN 'max 0' THEN 'none'
                WHEN 'none' THEN 'none'
                WHEN 'full' THEN 'full'
                WHEN 'unlimited' THEN 'full'
                WHEN 'max_2' THEN 'max_2'
                WHEN 'max 2' THEN 'max_2'
                ELSE LOWER(TRIM(dex_bonus_rule))
            END
            WHERE dex_bonus_rule IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET source = CASE LOWER(TRIM(source))
                WHEN 'admin' THEN 'admin_panel'
                WHEN 'admin_panel' THEN 'admin_panel'
                WHEN 'csv' THEN 'csv_import'
                WHEN 'csv_import' THEN 'csv_import'
                WHEN 'seed' THEN 'seed_json_bootstrap'
                WHEN 'seed_json_bootstrap' THEN 'seed_json_bootstrap'
                ELSE LOWER(TRIM(source))
            END
            WHERE source IS NOT NULL
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()

    equipment_category_enum = postgresql.ENUM(
        "adventuring_pack",
        "ammunition",
        "book",
        "clothing",
        "consumable_supply",
        "container",
        "document",
        "gaming_set",
        "insignia",
        "jewelry",
        "memento",
        "musical_instrument",
        "pet",
        "rope",
        "sailing_gear",
        "spellcasting_focus",
        "spellcasting_gear",
        "supplies",
        "tools",
        "trophy",
        "utility_tool",
        "vehicle_proficiency",
        "writing_supply",
        name="baseitemequipmentcategory",
        create_type=False,
    )
    damage_type_enum = postgresql.ENUM(
        "acid",
        "bludgeoning",
        "cold",
        "fire",
        "force",
        "lightning",
        "necrotic",
        "piercing",
        "poison",
        "psychic",
        "radiant",
        "slashing",
        "thunder",
        name="baseitemdamagetype",
        create_type=False,
    )
    dex_bonus_rule_enum = postgresql.ENUM(
        "full",
        "max_2",
        "none",
        name="baseitemdexbonusrule",
        create_type=False,
    )
    source_enum = postgresql.ENUM(
        "admin_panel",
        "csv_import",
        "seed_json_bootstrap",
        name="baseitemsource",
        create_type=False,
    )

    equipment_category_enum.create(bind, checkfirst=True)
    damage_type_enum.create(bind, checkfirst=True)
    dex_bonus_rule_enum.create(bind, checkfirst=True)
    source_enum.create(bind, checkfirst=True)

    _normalize_legacy_values()
    op.execute(sa.text("UPDATE base_item SET source = 'admin_panel' WHERE source IS NULL"))

    op.execute(
        sa.text(
            """
            ALTER TABLE base_item
            ALTER COLUMN equipment_category TYPE baseitemequipmentcategory
            USING equipment_category::baseitemequipmentcategory
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE base_item
            ALTER COLUMN damage_type TYPE baseitemdamagetype
            USING damage_type::baseitemdamagetype
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE base_item
            ALTER COLUMN dex_bonus_rule TYPE baseitemdexbonusrule
            USING dex_bonus_rule::baseitemdexbonusrule
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE base_item
            ALTER COLUMN source TYPE baseitemsource
            USING source::baseitemsource
            """
        )
    )
    op.alter_column(
        "base_item",
        "source",
        existing_type=source_enum,
        nullable=False,
        server_default="admin_panel",
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE item
            ALTER COLUMN damage_type TYPE baseitemdamagetype
            USING damage_type::baseitemdamagetype
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE item
            ALTER COLUMN dex_bonus_rule TYPE baseitemdexbonusrule
            USING dex_bonus_rule::baseitemdexbonusrule
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()

    equipment_category_enum = postgresql.ENUM(
        name="baseitemequipmentcategory",
        create_type=False,
    )
    damage_type_enum = postgresql.ENUM(
        name="baseitemdamagetype",
        create_type=False,
    )
    dex_bonus_rule_enum = postgresql.ENUM(
        name="baseitemdexbonusrule",
        create_type=False,
    )
    source_enum = postgresql.ENUM(
        name="baseitemsource",
        create_type=False,
    )

    op.alter_column(
        "base_item",
        "source",
        existing_type=source_enum,
        nullable=True,
        server_default=None,
    )
    op.execute(sa.text("ALTER TABLE item ALTER COLUMN dex_bonus_rule TYPE VARCHAR"))
    op.execute(sa.text("ALTER TABLE item ALTER COLUMN damage_type TYPE VARCHAR"))
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source TYPE VARCHAR"))
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN dex_bonus_rule TYPE VARCHAR"))
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN damage_type TYPE VARCHAR"))
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN equipment_category TYPE VARCHAR"))

    source_enum.drop(bind, checkfirst=True)
    dex_bonus_rule_enum.drop(bind, checkfirst=True)
    damage_type_enum.drop(bind, checkfirst=True)
    equipment_category_enum.drop(bind, checkfirst=True)
