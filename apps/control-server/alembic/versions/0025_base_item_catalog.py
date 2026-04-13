"""add_base_item_catalog

Revision ID: 0025_base_item_catalog
Revises: 0024_campaign_entities
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0025_base_item_catalog"
down_revision: Union[str, None] = "0024_campaign_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    system_enum = postgresql.ENUM(
        "DND5E",
        "T20",
        "PF2E",
        "COC",
        "CUSTOM",
        name="systemtype",
        create_type=False,
    )
    item_kind_enum = postgresql.ENUM(
        "weapon",
        "armor",
        "gear",
        "tool",
        "consumable",
        "focus",
        "ammo",
        "pack",
        name="baseitemkind",
        create_type=False,
    )
    cost_unit_enum = postgresql.ENUM(
        "cp",
        "sp",
        "ep",
        "gp",
        "pp",
        name="baseitemcostunit",
        create_type=False,
    )
    weapon_category_enum = postgresql.ENUM(
        "simple",
        "martial",
        name="baseitemweaponcategory",
        create_type=False,
    )
    weapon_range_type_enum = postgresql.ENUM(
        "melee",
        "ranged",
        name="baseitemweaponrangetype",
        create_type=False,
    )
    armor_category_enum = postgresql.ENUM(
        "light",
        "medium",
        "heavy",
        "shield",
        name="baseitemarmorcategory",
        create_type=False,
    )

    item_kind_enum.create(bind, checkfirst=True)
    cost_unit_enum.create(bind, checkfirst=True)
    weapon_category_enum.create(bind, checkfirst=True)
    weapon_range_type_enum.create(bind, checkfirst=True)
    armor_category_enum.create(bind, checkfirst=True)

    op.create_table(
        "base_item",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("system", system_enum, nullable=False),
        sa.Column("canonical_key", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pt", sa.String(), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_pt", sa.Text(), nullable=True),
        sa.Column("item_kind", item_kind_enum, nullable=False),
        sa.Column("equipment_category", sa.String(), nullable=True),
        sa.Column("cost_quantity", sa.Float(), nullable=True),
        sa.Column("cost_unit", cost_unit_enum, nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("weapon_category", weapon_category_enum, nullable=True),
        sa.Column("weapon_range_type", weapon_range_type_enum, nullable=True),
        sa.Column("damage_dice", sa.String(), nullable=True),
        sa.Column("damage_type", sa.String(), nullable=True),
        sa.Column("range_normal", sa.Integer(), nullable=True),
        sa.Column("range_long", sa.Integer(), nullable=True),
        sa.Column("versatile_damage", sa.String(), nullable=True),
        sa.Column(
            "weapon_properties_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("armor_category", armor_category_enum, nullable=True),
        sa.Column("armor_class_base", sa.Integer(), nullable=True),
        sa.Column("dex_bonus_rule", sa.String(), nullable=True),
        sa.Column("strength_requirement", sa.Integer(), nullable=True),
        sa.Column("stealth_disadvantage", sa.Boolean(), nullable=True),
        sa.Column(
            "is_shield",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_ref", sa.String(), nullable=True),
        sa.Column(
            "is_srd",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "system",
            "canonical_key",
            name="uq_base_item_system_canonical_key",
        ),
    )
    op.create_index("ix_base_item_system", "base_item", ["system"], unique=False)
    op.create_index(
        "ix_base_item_canonical_key",
        "base_item",
        ["canonical_key"],
        unique=False,
    )
    op.create_index("ix_base_item_item_kind", "base_item", ["item_kind"], unique=False)

    op.create_table(
        "base_item_alias",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("base_item_id", sa.String(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("locale", sa.String(), nullable=True),
        sa.Column("alias_type", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["base_item_id"],
            ["base_item.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_base_item_alias_base_item_id",
        "base_item_alias",
        ["base_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_base_item_alias_alias",
        "base_item_alias",
        ["alias"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    item_kind_enum = postgresql.ENUM(
        "weapon",
        "armor",
        "gear",
        "tool",
        "consumable",
        "focus",
        "ammo",
        "pack",
        name="baseitemkind",
        create_type=False,
    )
    cost_unit_enum = postgresql.ENUM(
        "cp",
        "sp",
        "ep",
        "gp",
        "pp",
        name="baseitemcostunit",
        create_type=False,
    )
    weapon_category_enum = postgresql.ENUM(
        "simple",
        "martial",
        name="baseitemweaponcategory",
        create_type=False,
    )
    weapon_range_type_enum = postgresql.ENUM(
        "melee",
        "ranged",
        name="baseitemweaponrangetype",
        create_type=False,
    )
    armor_category_enum = postgresql.ENUM(
        "light",
        "medium",
        "heavy",
        "shield",
        name="baseitemarmorcategory",
        create_type=False,
    )

    op.drop_index("ix_base_item_alias_alias", table_name="base_item_alias")
    op.drop_index("ix_base_item_alias_base_item_id", table_name="base_item_alias")
    op.drop_table("base_item_alias")

    op.drop_index("ix_base_item_item_kind", table_name="base_item")
    op.drop_index("ix_base_item_canonical_key", table_name="base_item")
    op.drop_index("ix_base_item_system", table_name="base_item")
    op.drop_table("base_item")

    armor_category_enum.drop(bind, checkfirst=True)
    weapon_range_type_enum.drop(bind, checkfirst=True)
    weapon_category_enum.drop(bind, checkfirst=True)
    cost_unit_enum.drop(bind, checkfirst=True)
    item_kind_enum.drop(bind, checkfirst=True)
