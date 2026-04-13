"""init

Revision ID: 0001_init
Revises:
Create Date: 2025-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "system",
            sa.Enum("DND5E", "T20", "PF2E", "COC", "CUSTOM", name="systemtype"),
            nullable=False,
        ),
        sa.Column(
            "role_mode",
            sa.Enum("GM", "PLAYER", name="rolemode"),
            nullable=False,
            server_default="GM",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "item",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("WEAPON", "ARMOR", "CONSUMABLE", "MISC", "MAGIC", name="itemtype"),
            nullable=False,
        ),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("price", sa.Float()),
        sa.Column("weight", sa.Float()),
        sa.Column("damage_dice", sa.String()),
        sa.Column("range_meters", sa.Float()),
        sa.Column(
            "properties",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_item_campaign_id", "item", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_item_campaign_id", table_name="item")
    op.drop_table("item")
    op.drop_table("campaign")
    op.execute("DROP TYPE IF EXISTS itemtype")
    op.execute("DROP TYPE IF EXISTS systemtype")
    op.execute("DROP TYPE IF EXISTS rolemode")
