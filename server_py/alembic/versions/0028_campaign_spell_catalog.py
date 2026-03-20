"""Campaign spell catalog snapshots.

Revision ID: 0028_campaign_spell_catalog
Revises: 0027_base_spell_catalog
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_campaign_spell_catalog"
down_revision: Union[str, None] = "0027_base_spell_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        "campaign_spell",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.String(),
            sa.ForeignKey("campaign.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "base_spell_id",
            sa.String(),
            sa.ForeignKey("base_spell.id"),
            nullable=True,
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
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "campaign_id",
            "canonical_key",
            name="uq_campaign_spell_campaign_canonical_key",
        ),
        sa.UniqueConstraint(
            "campaign_id",
            "base_spell_id",
            name="uq_campaign_spell_campaign_base_spell",
        ),
    )


def downgrade() -> None:
    op.drop_table("campaign_spell")
