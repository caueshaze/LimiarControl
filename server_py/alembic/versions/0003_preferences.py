"""preferences

Revision ID: 0003_preferences
Revises: 0002_inventory_npcs
Create Date: 2025-01-01 00:20:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_preferences"
down_revision = "0002_inventory_npcs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("selected_campaign_id", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("preferences")
