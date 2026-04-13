"""add party and session party fields

Revision ID: 0014_party_and_session
Revises: 0013_campaign_join_code
Create Date: 2026-02-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_party_and_session"
down_revision = "0013_campaign_join_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("GM", "PLAYER", name="rolemode", create_type=False)
    status_enum = postgresql.ENUM(
        "invited", "joined", name="partymemberstatus", create_type=False
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "party",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), sa.ForeignKey("campaign.id"), nullable=False),
        sa.Column("gm_user_id", sa.String(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_party_campaign_id", "party", ["campaign_id"])
    op.create_index("ix_party_gm_user_id", "party", ["gm_user_id"])

    op.create_table(
        "party_member",
        sa.Column("party_id", sa.String(), sa.ForeignKey("party.id"), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="joined"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_party_member_party_id", "party_member", ["party_id"])
    op.create_index("ix_party_member_user_id", "party_member", ["user_id"])

    op.add_column("campaign_session", sa.Column("party_id", sa.String(), nullable=True))
    op.add_column(
        "campaign_session", sa.Column("sequence_number", sa.Integer(), nullable=True)
    )
    op.create_index("ix_campaign_session_party_id", "campaign_session", ["party_id"])
    op.create_unique_constraint(
        "uq_campaign_session_party_sequence",
        "campaign_session",
        ["party_id", "sequence_number"],
    )

    op.execute(
        "UPDATE campaign_session SET sequence_number = number WHERE sequence_number IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_campaign_session_party_sequence", "campaign_session", type_="unique"
    )
    op.drop_index("ix_campaign_session_party_id", table_name="campaign_session")
    op.drop_column("campaign_session", "sequence_number")
    op.drop_column("campaign_session", "party_id")

    op.drop_index("ix_party_member_user_id", table_name="party_member")
    op.drop_index("ix_party_member_party_id", table_name="party_member")
    op.drop_table("party_member")

    op.drop_index("ix_party_gm_user_id", table_name="party")
    op.drop_index("ix_party_campaign_id", table_name="party")
    op.drop_table("party")

    status_enum = postgresql.ENUM(
        "invited", "joined", name="partymemberstatus", create_type=False
    )
    status_enum.drop(op.get_bind(), checkfirst=True)
