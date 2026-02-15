"""inventory and npcs

Revision ID: 0002_inventory_npcs
Revises: 0001_init
Create Date: 2025-01-01 00:10:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_inventory_npcs"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventoryitem",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("character_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_equipped", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_inventoryitem_campaign_id", "inventoryitem", ["campaign_id"])
    op.create_index("ix_inventoryitem_character_id", "inventoryitem", ["character_id"])
    op.create_index("ix_inventoryitem_item_id", "inventoryitem", ["item_id"])

    op.create_table(
        "npc",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("race", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("trait", sa.String(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("secret", sa.String()),
        sa.Column("notes", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_npc_campaign_id", "npc", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_npc_campaign_id", table_name="npc")
    op.drop_table("npc")
    op.drop_index("ix_inventoryitem_item_id", table_name="inventoryitem")
    op.drop_index("ix_inventoryitem_character_id", table_name="inventoryitem")
    op.drop_index("ix_inventoryitem_campaign_id", table_name="inventoryitem")
    op.drop_table("inventoryitem")
