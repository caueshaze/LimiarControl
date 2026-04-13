"""Allow deleting base spells without breaking campaign snapshots.

Revision ID: 0046_base_spell_delete_set_null
Revises: 0045_magic_item_spell_effects
Create Date: 2026-04-03
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0046_base_spell_delete_set_null"
down_revision: Union[str, None] = "0045_magic_item_spell_effects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "campaign_spell_base_spell_id_fkey",
        "campaign_spell",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "campaign_spell_base_spell_id_fkey",
        "campaign_spell",
        "base_spell",
        ["base_spell_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "campaign_spell_base_spell_id_fkey",
        "campaign_spell",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "campaign_spell_base_spell_id_fkey",
        "campaign_spell",
        "base_spell",
        ["base_spell_id"],
        ["id"],
    )
