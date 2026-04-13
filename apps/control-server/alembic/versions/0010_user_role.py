"""add user role

Revision ID: 0010_user_role
Revises: 0009_active_session
Create Date: 2026-01-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_user_role"
down_revision = "0009_active_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("GM", "PLAYER", name="rolemode", create_type=False)
    op.add_column(
        "app_user",
        sa.Column(
            "role",
            role_enum,
            nullable=False,
            server_default="PLAYER",
        ),
    )
    op.alter_column("app_user", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("app_user", "role")
