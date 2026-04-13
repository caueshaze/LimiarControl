"""Store selected tactical map on combat state.

Revision ID: 0048_combat_map_selection
Revises: 0047_campaign_map_config
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0048_combat_map_selection"
down_revision: Union[str, None] = "0047_campaign_map_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("combat_state", sa.Column("map_selection", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("combat_state", "map_selection")
