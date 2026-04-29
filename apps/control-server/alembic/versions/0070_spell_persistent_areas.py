"""add persistent area json columns for spells

Revision ID: 0070_spell_persistent_areas
Revises: 0069_spell_declarative_effects
Create Date: 2026-04-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0070_spell_persistent_areas"
down_revision = "0069_spell_declarative_effects"
branch_labels = None
depends_on = None


def _backfill_persistent_area(
    conn,
    *,
    table: str,
    canonical_key: str,
    payload: str,
) -> None:
    conn.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET persistent_area_json = CAST(:payload AS jsonb)
            WHERE canonical_key = :canonical_key AND persistent_area_json IS NULL
            """
        ),
        {
            "payload": payload,
            "canonical_key": canonical_key,
        },
    )


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column(
        "base_spell",
        sa.Column("persistent_area_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("persistent_area_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    _backfill_persistent_area(
        conn,
        table="base_spell",
        canonical_key="fog_cloud",
        payload='{"kind":"obscurement","params":{"obscurement":"heavily_obscured"}}',
    )
    _backfill_persistent_area(
        conn,
        table="base_spell",
        canonical_key="spike_growth",
        payload='{"kind":"hazard","params":{"terrainEffect":"difficult_terrain","movementDamageDice":"2d4","damageType":"Piercing","damagePerMeters":1.5}}',
    )
    _backfill_persistent_area(
        conn,
        table="campaign_spell",
        canonical_key="fog_cloud",
        payload='{"kind":"obscurement","params":{"obscurement":"heavily_obscured"}}',
    )
    _backfill_persistent_area(
        conn,
        table="campaign_spell",
        canonical_key="spike_growth",
        payload='{"kind":"hazard","params":{"terrainEffect":"difficult_terrain","movementDamageDice":"2d4","damageType":"Piercing","damagePerMeters":1.5}}',
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "persistent_area_json")
    op.drop_column("base_spell", "persistent_area_json")
