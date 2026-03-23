"""Replace legacy campaign entity combat fields with structured statblock fields.

Revision ID: 0033_entity_statblock
Revises: 0032_entity_combat_actions
Create Date: 2026-03-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0033_entity_statblock"
down_revision: Union[str, None] = "0032_entity_combat_actions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaign_entity", sa.Column("size", sa.Text(), nullable=True))
    op.add_column("campaign_entity", sa.Column("creature_type", sa.Text(), nullable=True))
    op.add_column("campaign_entity", sa.Column("creature_subtype", sa.Text(), nullable=True))
    op.add_column("campaign_entity", sa.Column("armor_class", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("max_hp", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("speed_meters", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("initiative_bonus", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("abilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("saving_throws", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("senses", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("spellcasting", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("damage_resistances", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("damage_immunities", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("damage_vulnerabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_entity", sa.Column("condition_immunities", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.drop_column("campaign_entity", "stats")
    op.drop_column("campaign_entity", "base_ac")
    op.drop_column("campaign_entity", "base_hp")


def downgrade() -> None:
    op.add_column("campaign_entity", sa.Column("base_hp", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("base_ac", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.drop_column("campaign_entity", "condition_immunities")
    op.drop_column("campaign_entity", "damage_vulnerabilities")
    op.drop_column("campaign_entity", "damage_immunities")
    op.drop_column("campaign_entity", "damage_resistances")
    op.drop_column("campaign_entity", "spellcasting")
    op.drop_column("campaign_entity", "senses")
    op.drop_column("campaign_entity", "skills")
    op.drop_column("campaign_entity", "saving_throws")
    op.drop_column("campaign_entity", "abilities")
    op.drop_column("campaign_entity", "initiative_bonus")
    op.drop_column("campaign_entity", "speed_meters")
    op.drop_column("campaign_entity", "max_hp")
    op.drop_column("campaign_entity", "armor_class")
    op.drop_column("campaign_entity", "creature_subtype")
    op.drop_column("campaign_entity", "creature_type")
    op.drop_column("campaign_entity", "size")
