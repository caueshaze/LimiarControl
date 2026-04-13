"""Add structured save success outcome to spell catalogs.

Revision ID: 0034_spell_save_success_outcome
Revises: 0033_entity_statblock
Create Date: 2026-03-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0034_spell_save_success_outcome"
down_revision: Union[str, None] = "0033_entity_statblock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("base_spell", sa.Column("save_success_outcome", sa.String(), nullable=True))
    op.add_column("campaign_spell", sa.Column("save_success_outcome", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_spell", "save_success_outcome")
    op.drop_column("base_spell", "save_success_outcome")
