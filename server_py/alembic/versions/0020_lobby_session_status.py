"""add_lobby_session_status

Revision ID: 0020_lobby_session_status
Revises: dc5a16d1b899
Create Date: 2026-03-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0020_lobby_session_status"
down_revision: Union[str, None] = "dc5a16d1b899"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'LOBBY'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; no-op
    pass
