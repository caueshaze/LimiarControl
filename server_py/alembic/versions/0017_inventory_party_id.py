"""add party_id to inventory_item

Revision ID: 0017_inventory_party_id
Revises: 57d7e3a6b345_remove_join_code
Create Date: 2026-03-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_inventory_party_id"
down_revision = "57d7e3a6b345"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventoryitem",
        sa.Column("party_id", sa.String(), sa.ForeignKey("party.id"), nullable=True),
    )
    op.create_index("ix_inventoryitem_party_id", "inventoryitem", ["party_id"])


def downgrade() -> None:
    op.drop_index("ix_inventoryitem_party_id", table_name="inventoryitem")
    op.drop_column("inventoryitem", "party_id")
