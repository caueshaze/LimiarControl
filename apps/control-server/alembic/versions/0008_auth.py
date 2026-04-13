"""auth users and member linkage

Revision ID: 0008_auth
Revises: 0007_drop_campaign_join_code
Create Date: 2025-01-01 01:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_auth"
down_revision = "0007_drop_campaign_join_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("display_name", sa.String()),
        sa.Column("pin_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_app_user_username", "app_user", ["username"], unique=True)

    op.drop_table("campaign_member")
    role_mode_enum = postgresql.ENUM("GM", "PLAYER", name="rolemode", create_type=False)
    op.create_table(
        "campaign_member",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role_mode", role_mode_enum, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "user_id"),
    )
    op.create_index("ix_campaign_member_campaign_id", "campaign_member", ["campaign_id"])
    op.create_index("ix_campaign_member_user_id", "campaign_member", ["user_id"])

    op.drop_table("inventoryitem")
    op.create_table(
        "inventoryitem",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("member_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("is_equipped", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["campaign_member.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_inventoryitem_campaign_id", "inventoryitem", ["campaign_id"])
    op.create_index("ix_inventoryitem_member_id", "inventoryitem", ["member_id"])
    op.create_index("ix_inventoryitem_item_id", "inventoryitem", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_inventoryitem_item_id", table_name="inventoryitem")
    op.drop_index("ix_inventoryitem_member_id", table_name="inventoryitem")
    op.drop_index("ix_inventoryitem_campaign_id", table_name="inventoryitem")
    op.drop_table("inventoryitem")

    op.drop_index("ix_campaign_member_user_id", table_name="campaign_member")
    op.drop_index("ix_campaign_member_campaign_id", table_name="campaign_member")
    op.drop_table("campaign_member")

    op.drop_index("ix_app_user_username", table_name="app_user")
    op.drop_table("app_user")
