"""Add structured combat actions to campaign entities.

Revision ID: 0032_entity_combat_actions
Revises: 563684764260
Create Date: 2026-03-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0032_entity_combat_actions"
down_revision: Union[str, None] = "563684764260"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_entity",
        sa.Column("combat_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_entity", "combat_actions")
