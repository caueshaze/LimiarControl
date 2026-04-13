"""Add campaign-item columns to item table (base_item_id, snapshots, item_kind, etc.)

Revision ID: 0026_campaign_item_columns
Revises: 0025_base_item_catalog
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0026_campaign_item_columns"
down_revision: Union[str, None] = "0025_base_item_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("item", sa.Column("base_item_id", sa.String(), nullable=True))
    op.add_column("item", sa.Column("canonical_key_snapshot", sa.String(), nullable=True))
    op.add_column("item", sa.Column("name_en_snapshot", sa.String(), nullable=True))
    op.add_column("item", sa.Column("name_pt_snapshot", sa.String(), nullable=True))
    op.add_column(
        "item",
        sa.Column(
            "item_kind",
            sa.Enum(
                "weapon", "armor", "gear", "tool", "consumable", "focus", "ammo", "pack",
                name="baseitemkind",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "item",
        sa.Column(
            "cost_unit",
            sa.Enum(
                "cp", "sp", "ep", "gp", "pp",
                name="baseitemcostunit",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "item",
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "item",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_index("ix_item_base_item_id", "item", ["base_item_id"])
    op.create_foreign_key(
        "fk_item_base_item_id",
        "item",
        "base_item",
        ["base_item_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_item_campaign_base_item",
        "item",
        ["campaign_id", "base_item_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_item_campaign_base_item", "item", type_="unique")
    op.drop_constraint("fk_item_base_item_id", "item", type_="foreignkey")
    op.drop_index("ix_item_base_item_id", table_name="item")
    op.drop_column("item", "is_enabled")
    op.drop_column("item", "is_custom")
    op.drop_column("item", "cost_unit")
    op.drop_column("item", "item_kind")
    op.drop_column("item", "name_pt_snapshot")
    op.drop_column("item", "name_en_snapshot")
    op.drop_column("item", "canonical_key_snapshot")
    op.drop_column("item", "base_item_id")
