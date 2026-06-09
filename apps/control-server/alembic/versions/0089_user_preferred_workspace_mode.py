"""add user preferred workspace mode

Revision ID: 0089_user_preferred_workspace_mode
Revises: 0088_magic_bracelet_category_and_item_equipment_category
Create Date: 2026-06-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0089_user_preferred_workspace_mode"
down_revision = "0088_magic_bracelet_category_and_item_equipment_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column(
            "preferred_workspace_mode",
            sa.Enum("GM", "PLAYER", name="rolemode", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("app_user", "preferred_workspace_mode")
