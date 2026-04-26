"""Add max_targets to spell catalogs.

Revision ID: 0067_spell_max_targets
Revises: 0066_active_area_effects
Create Date: 2026-04-25 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0067_spell_max_targets"
down_revision: Union[str, None] = "0066_active_area_effects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("base_spell", "campaign_spell")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("max_targets", sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "max_targets")
