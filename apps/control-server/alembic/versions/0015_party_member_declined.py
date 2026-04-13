"""add party member declined status

Revision ID: 0015_party_member_declined
Revises: 0014_party_and_session
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_party_member_declined"
down_revision = "0014_party_and_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_enum = postgresql.ENUM(
        "invited", "joined", "declined", name="partymemberstatus", create_type=False
    )
    status_enum.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE partymemberstatus ADD VALUE IF NOT EXISTS 'declined'")


def downgrade() -> None:
    # Postgres does not support removing enum values without type recreation.
    pass
