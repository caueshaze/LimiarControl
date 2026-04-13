"""Add global system admin permission and clean base item deletion behavior.

Revision ID: 0035_system_admin_base_items
Revises: 0034_spell_save_success_outcome
Create Date: 2026-03-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0035_system_admin_base_items"
down_revision: Union[str, None] = "0034_spell_save_success_outcome"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column("is_system_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        sa.text(
            """
            UPDATE app_user
            SET is_system_admin = TRUE
            WHERE role = 'GM'
            """
        )
    )

    op.drop_constraint("fk_item_base_item_id", "item", type_="foreignkey")
    op.create_foreign_key(
        "fk_item_base_item_id",
        "item",
        "base_item",
        ["base_item_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_item_base_item_id", "item", type_="foreignkey")
    op.create_foreign_key(
        "fk_item_base_item_id",
        "item",
        "base_item",
        ["base_item_id"],
        ["id"],
    )
    op.drop_column("app_user", "is_system_admin")
