"""sessions

Revision ID: 0006_sessions
Revises: 0005_identity
Create Date: 2025-01-01 01:00:00
"""

import random
import string
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0006_sessions"
down_revision = "0005_identity"
branch_labels = None
depends_on = None

JOIN_CODE_CHARS = string.ascii_uppercase + string.digits


def generate_join_code() -> str:
    length = random.randint(6, 8)
    return "".join(random.choice(JOIN_CODE_CHARS) for _ in range(length))


def upgrade() -> None:
    op.create_table(
        "campaign_session",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String()),
        sa.Column("join_code", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_campaign_session_campaign_id", "campaign_session", ["campaign_id"]
    )
    op.create_index("ix_campaign_session_join_code", "campaign_session", ["join_code"], unique=True)

    op.add_column("roll_event", sa.Column("session_id", sa.String(), nullable=True))
    op.create_index("ix_roll_event_session_id", "roll_event", ["session_id"])
    op.create_foreign_key(
        "fk_roll_event_session_id",
        "roll_event",
        "campaign_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )

    connection = op.get_bind()
    campaigns = connection.execute(sa.text("SELECT id FROM campaign")).fetchall()
    used_codes: set[str] = set()
    for (campaign_id,) in campaigns:
        code = generate_join_code()
        while code in used_codes:
            code = generate_join_code()
        used_codes.add(code)
        session_id = str(uuid4())
        connection.execute(
            sa.text(
                "INSERT INTO campaign_session (id, campaign_id, number, title, join_code) "
                "VALUES (:id, :campaign_id, :number, :title, :join_code)"
            ),
            {
                "id": str(session_id),
                "campaign_id": campaign_id,
                "number": 1,
                "title": "Sessao 1",
                "join_code": code,
            },
        )

        connection.execute(
            sa.text(
                "UPDATE roll_event SET session_id = :session_id WHERE campaign_id = :campaign_id"
            ),
            {"session_id": session_id, "campaign_id": campaign_id},
        )

    op.alter_column("roll_event", "session_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_roll_event_session_id", "roll_event", type_="foreignkey")
    op.drop_index("ix_roll_event_session_id", table_name="roll_event")
    op.drop_column("roll_event", "session_id")
    op.drop_index("ix_campaign_session_join_code", table_name="campaign_session")
    op.drop_index("ix_campaign_session_campaign_id", table_name="campaign_session")
    op.drop_table("campaign_session")
