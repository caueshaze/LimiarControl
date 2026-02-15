"""add campaign join_code

Revision ID: 0013_campaign_join_code
Revises: 0012_session_status_state
Create Date: 2026-01-28
"""

from __future__ import annotations

import random
import string

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0013_campaign_join_code"
down_revision = "0012_session_status_state"
branch_labels = None
depends_on = None

JOIN_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_code(length: int = 8) -> str:
    return "".join(random.choice(JOIN_CODE_CHARS) for _ in range(length))


def upgrade() -> None:
    op.add_column("campaign", sa.Column("join_code", sa.String(), nullable=True))
    bind = op.get_bind()
    existing_codes = set()
    rows = bind.execute(sa.text("SELECT id FROM campaign")).fetchall()
    for (campaign_id,) in rows:
        code = _generate_code()
        while code in existing_codes:
            code = _generate_code()
        existing_codes.add(code)
        bind.execute(
            sa.text("UPDATE campaign SET join_code = :code WHERE id = :cid"),
            {"code": code, "cid": campaign_id},
        )
    op.create_unique_constraint("uq_campaign_join_code", "campaign", ["join_code"])
    op.create_index("ix_campaign_join_code", "campaign", ["join_code"], unique=True)
    op.alter_column("campaign", "join_code", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_campaign_join_code", table_name="campaign")
    op.drop_constraint("uq_campaign_join_code", "campaign", type_="unique")
    op.drop_column("campaign", "join_code")
