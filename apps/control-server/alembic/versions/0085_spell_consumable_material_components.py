"""add consumed material component fields to spell catalogs

Revision ID: 0085_spell_consumable_material_components
Revises: 0084_attack_miss_outcome
Create Date: 2026-05-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0085_spell_consumable_material_components"
down_revision = "0084_attack_miss_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("material_component_consumed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "base_spell",
        sa.Column("consumable_material_options_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("material_component_consumed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("consumable_material_options_json", sa.JSON(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE base_spell
               SET material_component_consumed = true,
                   consumable_material_options_json = '[
                     {"key":"holy_water","nameEn":"Holy water","namePt":"Água benta","quantity":1},
                     {"key":"powdered_silver_and_iron","nameEn":"Powdered silver and iron","namePt":"Prata e ferro em pó","quantity":1}
                   ]'::jsonb
             WHERE canonical_key = 'protection_from_evil_and_good'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE campaign_spell
               SET material_component_consumed = true,
                   consumable_material_options_json = '[
                     {"key":"holy_water","nameEn":"Holy water","namePt":"Água benta","quantity":1},
                     {"key":"powdered_silver_and_iron","nameEn":"Powdered silver and iron","namePt":"Prata e ferro em pó","quantity":1}
                   ]'::jsonb
             WHERE canonical_key = 'protection_from_evil_and_good'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "consumable_material_options_json")
    op.drop_column("campaign_spell", "material_component_consumed")
    op.drop_column("base_spell", "consumable_material_options_json")
    op.drop_column("base_spell", "material_component_consumed")
