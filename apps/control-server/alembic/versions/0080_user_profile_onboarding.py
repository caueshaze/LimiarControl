"""add user profile + onboarding fields

Revision ID: 0080_user_profile_onboarding
Revises: 0079_inventory_condition_tags
Create Date: 2026-05-12 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0080_user_profile_onboarding"
down_revision = "0079_inventory_condition_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_user", sa.Column("avatar_url", sa.String(), nullable=True))
    op.add_column("app_user", sa.Column("token_color", sa.String(length=9), nullable=True))
    op.add_column("app_user", sa.Column("token_image_url", sa.String(), nullable=True))
    op.add_column(
        "app_user",
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing users are not forced through the onboarding flow.
    op.execute("UPDATE app_user SET onboarded_at = NOW() WHERE onboarded_at IS NULL")


def downgrade() -> None:
    op.drop_column("app_user", "onboarded_at")
    op.drop_column("app_user", "token_image_url")
    op.drop_column("app_user", "token_color")
    op.drop_column("app_user", "avatar_url")
