"""add out_of_combat_castable to base_spell and campaign_spell

Revision ID: 0020_add_out_of_combat_castable
Revises: dc5a16d1b899
Create Date: 2026-05-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_add_out_of_combat_castable"
down_revision: Union[str, None] = "dc5a16d1b899"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column("out_of_combat_castable", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "campaign_spell",
        sa.Column("out_of_combat_castable", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("base_spell", "out_of_combat_castable")
    op.drop_column("campaign_spell", "out_of_combat_castable")
