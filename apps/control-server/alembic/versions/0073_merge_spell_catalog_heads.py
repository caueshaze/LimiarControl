"""merge spell catalog heads

Revision ID: 0073_merge_spell_catalog_heads
Revises: 0020_add_out_of_combat_castable, 0072_out_of_combat_target
Create Date: 2026-05-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0073_merge_spell_catalog_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0020_add_out_of_combat_castable",
    "0072_out_of_combat_target",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
