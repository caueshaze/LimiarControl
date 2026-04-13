"""Add cover_applies_to_save field to base_spell catalog.

Governs whether cover modifies the effective DC for saving throw resolution:
  "physical" → cover applies (spatial/blast effects such as fireball, thunderwave)
  "none"     → cover does not apply (mental/control effects such as hold_person)
  NULL       → fallback heuristic used during migration (DEX saves assumed physical)

Revision ID: 0052_base_spell_cover_applies_to_save
Revises: 0051_spell_targeting_requirements
Create Date: 2026-04-05 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0052_base_spell_cover_applies_to_save"
down_revision: Union[str, None] = "0051_spell_targeting_requirements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("cover_applies_to_save", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("base_spell", "cover_applies_to_save")
