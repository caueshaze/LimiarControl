"""preferences per user

Revision ID: 0011_preferences_user
Revises: 0010_user_role
Create Date: 2026-01-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_preferences_user"
down_revision = "0010_user_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM preferences")
    op.add_column(
        "preferences",
        sa.Column("user_id", sa.String(), nullable=False),
    )
    op.create_foreign_key(
        "preferences_user_id_fkey",
        "preferences",
        "app_user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "preferences_user_id_key", "preferences", ["user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("preferences_user_id_key", "preferences", type_="unique")
    op.drop_constraint("preferences_user_id_fkey", "preferences", type_="foreignkey")
    op.drop_column("preferences", "user_id")
