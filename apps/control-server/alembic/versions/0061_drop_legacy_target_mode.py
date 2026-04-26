"""Drop legacy target_mode column from base_spell and campaign_spell.

The 0060 migration added target_type + area_shape and was supposed to drop
target_mode, but the drop was missing when the migration first ran locally.
This migration completes the cleanup. Newer checkouts have 0060 already doing
that drop, so the upgrade is intentionally tolerant of either schema state.

Revision ID: 0061_drop_legacy_target_mode
Revises: 0060_spell_target_type_area_shape
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0061_drop_legacy_target_mode"
down_revision: Union[str, None] = "0060_spell_target_type_area_shape"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("base_spell", "campaign_spell"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS target_mode")


def downgrade() -> None:
    # Compatibility cleanup only; revision 0060 is the source of truth for
    # translating target_type + area_shape back to target_mode.
    pass
