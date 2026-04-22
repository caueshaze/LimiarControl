"""Add area_size_meters to base_spell and campaign_spell.

Stores the AoE radius / side-length in meters for area spells (sphere, cone,
line, cube, cylinder).  When set, the combat targeting layer reads this value directly
from the spell catalog instead of falling back to the hardcoded
_SUPPORTED_AREA_SPELL_SPECS dictionary, enabling campaign-created spells to
author their own map targeting geometry without backend code changes.

Revision ID: 0054_spell_area_size_meters
Revises: 0053_campaign_spell_cover_applies_to_save
Create Date: 2026-04-13 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0054_spell_area_size_meters"
down_revision: Union[str, None] = "0053_campaign_spell_cover_applies_to_save"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("area_size_meters", sa.Integer(), nullable=True),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("area_size_meters", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "area_size_meters")
    op.drop_column("base_spell", "area_size_meters")
