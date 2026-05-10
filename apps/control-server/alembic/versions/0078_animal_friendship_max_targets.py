"""Set max_targets = 1 for Animal Friendship to enable upcast target scaling.

Revision ID: 0078_animal_friendship_max_targets
Revises: 0077_mage_armor_data
Create Date: 2026-05-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0078_animal_friendship_max_targets"
down_revision = "0077_mage_armor_data"
branch_labels = None
depends_on = None

_SYSTEM = "DND5E"
_CANONICAL_KEY = "animal_friendship"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE base_spell SET max_targets = 1 "
            "WHERE system = :sys AND canonical_key = :key AND max_targets IS NULL"
        ),
        {"sys": _SYSTEM, "key": _CANONICAL_KEY},
    )
    conn.execute(
        sa.text(
            "UPDATE campaign_spell SET max_targets = 1 "
            "WHERE canonical_key = :key AND is_custom = false AND max_targets IS NULL"
        ),
        {"key": _CANONICAL_KEY},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE base_spell SET max_targets = NULL "
            "WHERE system = :sys AND canonical_key = :key AND max_targets = 1"
        ),
        {"sys": _SYSTEM, "key": _CANONICAL_KEY},
    )
    conn.execute(
        sa.text(
            "UPDATE campaign_spell SET max_targets = NULL "
            "WHERE canonical_key = :key AND is_custom = false AND max_targets = 1"
        ),
        {"key": _CANONICAL_KEY},
    )
