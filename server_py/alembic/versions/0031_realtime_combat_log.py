"""Add combat runtime and structured activity payloads.

Revision ID: 0031_realtime_combat_log
Revises: 0030_item_automation_fields
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0031_realtime_combat_log"
down_revision: Union[str, None] = "0030_item_automation_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_command_event",
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "session_runtime",
        sa.Column(
            "combat_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("session_runtime", "combat_active")
    op.drop_column("session_command_event", "payload_json")
