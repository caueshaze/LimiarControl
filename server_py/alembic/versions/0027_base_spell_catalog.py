"""Base spell catalog tables.

Revision ID: 0027_base_spell_catalog
Revises: 0026_campaign_item_columns
"""
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0027_base_spell_catalog"
down_revision: Union[str, None] = "0026_campaign_item_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the spellschool enum if it doesn't exist yet
    spellschool_enum = postgresql.ENUM(
        "abjuration",
        "conjuration",
        "divination",
        "enchantment",
        "evocation",
        "illusion",
        "necromancy",
        "transmutation",
        name="spellschool",
        create_type=False,
    )
    spellschool_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "base_spell",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "system",
            postgresql.ENUM("DND5E", "T20", "PF2E", "COC", "CUSTOM", name="systemtype", create_type=False),
            nullable=False,
            index=True,
        ),
        sa.Column("canonical_key", sa.String(), nullable=False, index=True),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pt", sa.String(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("description_pt", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, index=True),
        sa.Column("school", spellschool_enum, nullable=False, index=True),
        sa.Column("classes_json", postgresql.JSONB(), nullable=True),
        sa.Column("casting_time", sa.String(), nullable=True),
        sa.Column("range_text", sa.String(), nullable=True),
        sa.Column("duration", sa.String(), nullable=True),
        sa.Column("components_json", postgresql.JSONB(), nullable=True),
        sa.Column("material_component_text", sa.Text(), nullable=True),
        sa.Column("concentration", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ritual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("damage_type", sa.String(), nullable=True),
        sa.Column("saving_throw", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_ref", sa.String(), nullable=True),
        sa.Column("is_srd", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("system", "canonical_key", name="uq_base_spell_system_canonical_key"),
    )

    op.create_table(
        "base_spell_alias",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "base_spell_id",
            sa.String(),
            sa.ForeignKey("base_spell.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("alias", sa.String(), nullable=False, index=True),
        sa.Column("locale", sa.String(), nullable=True),
        sa.Column("alias_type", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("base_spell_alias")
    op.drop_table("base_spell")
    postgresql.ENUM(name="spellschool").drop(op.get_bind(), checkfirst=True)
