"""Add structured upcast JSON to spell catalogs.

Revision ID: 0043_spell_structured_upcast
Revises: 0042_inventory_temporary_item_metadata
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0043_spell_structured_upcast"
down_revision: Union[str, None] = "0042_inventory_temporary_item_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _legacy_upcast_to_json(
    *,
    resolution_type: str | None,
    upcast_mode: str | None,
    upcast_value: str | None,
) -> dict | None:
    normalized_mode = (upcast_mode or "").strip()
    normalized_value = (upcast_value or "").strip()
    if not normalized_mode or normalized_mode == "none":
        return None
    if normalized_mode == "add_dice" and normalized_value:
        return {
            "mode": "add_heal" if resolution_type == "heal" else "add_damage",
            "dice": normalized_value,
            "perLevel": 1,
        }
    if normalized_mode == "add_targets":
        per_level = int(normalized_value) if normalized_value.isdigit() and int(normalized_value) > 0 else 1
        return {
            "mode": "increase_targets",
            "perLevel": per_level,
        }
    if normalized_mode in {"increase_duration", "custom"}:
        return {"mode": "custom", "perLevel": 1}
    return None


def _backfill_structured_upcast(table_name: str) -> None:
    connection = op.get_bind()
    spell_table = sa.table(
        table_name,
        sa.column("id", sa.String()),
        sa.column("resolution_type", sa.String()),
        sa.column("upcast_mode", sa.String()),
        sa.column("upcast_value", sa.String()),
        sa.column("upcast_json", postgresql.JSONB(astext_type=sa.Text())),
    )

    rows = connection.execute(
        sa.select(
            spell_table.c.id,
            spell_table.c.resolution_type,
            spell_table.c.upcast_mode,
            spell_table.c.upcast_value,
        )
    ).mappings()

    for row in rows:
        upcast_json = _legacy_upcast_to_json(
            resolution_type=row["resolution_type"],
            upcast_mode=row["upcast_mode"],
            upcast_value=row["upcast_value"],
        )
        if upcast_json is None:
            continue
        connection.execute(
            spell_table.update()
            .where(spell_table.c.id == row["id"])
            .values(upcast_json=upcast_json)
        )


def upgrade() -> None:
    op.add_column("base_spell", sa.Column("upcast_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaign_spell", sa.Column("upcast_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    _backfill_structured_upcast("base_spell")
    _backfill_structured_upcast("campaign_spell")


def downgrade() -> None:
    op.drop_column("campaign_spell", "upcast_json")
    op.drop_column("base_spell", "upcast_json")
