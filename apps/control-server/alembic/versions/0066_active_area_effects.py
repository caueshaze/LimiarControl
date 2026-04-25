"""Add persistent combat active area effects.

Revision ID: 0066_active_area_effects
Revises: 0065_spell_targeting_semantics
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0066_active_area_effects"
down_revision: Union[str, None] = "0065_spell_targeting_semantics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "combat_state",
        sa.Column(
            "active_area_effects",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("combat_state", "active_area_effects")
