"""add party member left status

Revision ID: 0016_party_member_left
Revises: 0015_party_member_declined
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_party_member_left"
down_revision = "0015_party_member_declined"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_enum = postgresql.ENUM(
        "invited", "joined", "declined", "left", name="partymemberstatus", create_type=False
    )
    status_enum.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE partymemberstatus ADD VALUE IF NOT EXISTS 'left'")


def downgrade() -> None:
    # Postgres does not support removing enum values without type recreation.
    pass
