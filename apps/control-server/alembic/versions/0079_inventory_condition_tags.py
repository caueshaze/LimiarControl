"""add inventory condition tags

Revision ID: 0079_inventory_condition_tags
Revises: 0078_animal_friendship_max_targets
Create Date: 2026-05-12 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0079_inventory_condition_tags"
down_revision = "0078_animal_friendship_max_targets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventoryitem",
        sa.Column(
            "condition_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("inventoryitem", "condition_tags")

