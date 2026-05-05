"""Add out_of_combat_target to spell catalogs.

Revision ID: 0072_out_of_combat_target
Revises: 0071_spell_variants
Create Date: 2026-05-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0072_out_of_combat_target"
down_revision = "0071_spell_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "base_spell",
        sa.Column(
            "out_of_combat_target",
            sa.String(20),
            nullable=False,
            server_default="self",
        ),
    )
    op.add_column(
        "campaign_spell",
        sa.Column(
            "out_of_combat_target",
            sa.String(20),
            nullable=False,
            server_default="self",
        ),
    )


def downgrade() -> None:
    op.drop_column("base_spell", "out_of_combat_target")
    op.drop_column("campaign_spell", "out_of_combat_target")
