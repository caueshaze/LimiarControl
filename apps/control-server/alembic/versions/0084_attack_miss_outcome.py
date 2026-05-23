"""add attack miss outcome to spell catalogs

Revision ID: 0084_attack_miss_outcome
Revises: 0083_spell_attack_advantage_condition, 0083_spell_requires_target_hearing
Create Date: 2026-05-22 23:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0084_attack_miss_outcome"
down_revision = ("0083_spell_attack_advantage_condition", "0083_spell_requires_target_hearing")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("base_spell", sa.Column("attack_miss_outcome", sa.String(), nullable=True))
    op.add_column("campaign_spell", sa.Column("attack_miss_outcome", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_spell", "attack_miss_outcome")
    op.drop_column("base_spell", "attack_miss_outcome")

