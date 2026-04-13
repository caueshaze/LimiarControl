"""identity lite

Revision ID: 0005_identity
Revises: 0004_roll_events
Create Date: 2025-01-01 00:45:00
"""

import random
import string

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_identity"
down_revision = "0004_roll_events"
branch_labels = None
depends_on = None

JOIN_CODE_CHARS = string.ascii_uppercase + string.digits


def generate_join_code() -> str:
    length = random.randint(6, 8)
    return "".join(random.choice(JOIN_CODE_CHARS) for _ in range(length))


def upgrade() -> None:
    op.add_column("campaign", sa.Column("join_code", sa.String(), nullable=True))

    connection = op.get_bind()
    campaigns = connection.execute(sa.text("SELECT id FROM campaign")).fetchall()
    used_codes: set[str] = set()
    for (campaign_id,) in campaigns:
        code = generate_join_code()
        while code in used_codes:
            code = generate_join_code()
        used_codes.add(code)
        connection.execute(
            sa.text("UPDATE campaign SET join_code = :code WHERE id = :id"),
            {"code": code, "id": campaign_id},
        )

    op.alter_column("campaign", "join_code", nullable=False)
    op.create_index("ix_campaign_join_code", "campaign", ["join_code"], unique=True)

    role_mode_enum = postgresql.ENUM(
        "GM", "PLAYER", name="rolemode", create_type=False
    )
    op.create_table(
        "campaign_member",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role_mode", role_mode_enum, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "device_id"),
    )
    op.create_index("ix_campaign_member_campaign_id", "campaign_member", ["campaign_id"])
    op.create_index("ix_campaign_member_device_id", "campaign_member", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_campaign_member_device_id", table_name="campaign_member")
    op.drop_index("ix_campaign_member_campaign_id", table_name="campaign_member")
    op.drop_table("campaign_member")
    op.drop_index("ix_campaign_join_code", table_name="campaign")
    op.drop_column("campaign", "join_code")
