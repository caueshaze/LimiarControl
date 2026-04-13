"""Add cover_applies_to_save field to campaign_spell catalog.

Mirrors the same field already present on base_spell (migration 0052).
Governs whether cover modifies the effective DC for saving throw resolution:
  "physical" → cover applies (spatial/blast effects such as fireball, thunderwave)
  "none"     → cover does not apply (mental/control effects such as hold_person)
  NULL       → fallback heuristic used for records that pre-date this field
               (DEX saves assumed physical)

Revision ID: 0053_campaign_spell_cover_applies_to_save
Revises: 0052_base_spell_cover_applies_to_save
Create Date: 2026-04-06 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0053_campaign_spell_cover_applies_to_save"
down_revision: Union[str, None] = "0052_base_spell_cover_applies_to_save"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_spell",
        sa.Column("cover_applies_to_save", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_spell", "cover_applies_to_save")
