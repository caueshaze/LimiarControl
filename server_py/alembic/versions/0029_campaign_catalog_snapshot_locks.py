"""Lock campaign catalog snapshots at creation time.

Revision ID: 0029_catalog_snapshot_lock
Revises: 0028_campaign_spell_catalog
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_catalog_snapshot_lock"
down_revision: Union[str, None] = "0028_campaign_spell_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign",
        sa.Column("item_catalog_snapshot_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign",
        sa.Column("spell_catalog_snapshot_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Freeze all existing campaigns to their current state so later base-catalog
    # changes cannot silently backfill or overwrite their isolated snapshots.
    op.execute(
        sa.text(
            """
            UPDATE campaign
            SET item_catalog_snapshot_at = COALESCE(item_catalog_snapshot_at, created_at),
                spell_catalog_snapshot_at = COALESCE(spell_catalog_snapshot_at, created_at)
            """
        )
    )


def downgrade() -> None:
    op.drop_column("campaign", "spell_catalog_snapshot_at")
    op.drop_column("campaign", "item_catalog_snapshot_at")
