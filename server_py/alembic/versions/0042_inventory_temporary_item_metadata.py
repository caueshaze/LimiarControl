"""Add temporary-item metadata to inventory entries.

Revision ID: 0042_inventory_temporary_item_metadata
Revises: 0041_party_character_sheet_drafts
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0042_inventory_temporary_item_metadata"
down_revision: Union[str, None] = "0041_party_character_sheet_drafts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventoryitem", sa.Column("source_spell_canonical_key", sa.String(), nullable=True))
    op.add_column("inventoryitem", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f("ix_inventoryitem_source_spell_canonical_key"),
        "inventoryitem",
        ["source_spell_canonical_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventoryitem_expires_at"),
        "inventoryitem",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inventoryitem_expires_at"), table_name="inventoryitem")
    op.drop_index(op.f("ix_inventoryitem_source_spell_canonical_key"), table_name="inventoryitem")
    op.drop_column("inventoryitem", "expires_at")
    op.drop_column("inventoryitem", "source_spell_canonical_key")
