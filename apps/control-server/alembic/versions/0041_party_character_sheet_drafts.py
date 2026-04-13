"""Add party character sheet drafts and delivery metadata.

Revision ID: 0041_party_character_sheet_drafts
Revises: 0040_healing_consumable_columns
Create Date: 2026-03-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041_party_character_sheet_drafts"
down_revision: Union[str, None] = "0040_healing_consumable_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

    draft_status_enum = postgresql.ENUM(
        "active",
        "archived",
        name="partycharactersheetdraftstatus",
    )
    draft_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "party_character_sheet_draft",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "archived",
                name="partycharactersheetdraftstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_derived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["party_id"], ["party.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_party_character_sheet_draft_party_id"),
        "party_character_sheet_draft",
        ["party_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_party_character_sheet_draft_created_by_user_id"),
        "party_character_sheet_draft",
        ["created_by_user_id"],
        unique=False,
    )

    op.add_column("character_sheet", sa.Column("source_draft_id", sa.String(), nullable=True))
    op.add_column("character_sheet", sa.Column("delivered_by_user_id", sa.String(), nullable=True))
    op.add_column("character_sheet", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("character_sheet", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f("ix_character_sheet_source_draft_id"),
        "character_sheet",
        ["source_draft_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_character_sheet_delivered_by_user_id"),
        "character_sheet",
        ["delivered_by_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_character_sheet_source_draft_id_party_character_sheet_draft",
        "character_sheet",
        "party_character_sheet_draft",
        ["source_draft_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_character_sheet_delivered_by_user_id_app_user",
        "character_sheet",
        "app_user",
        ["delivered_by_user_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE character_sheet
            SET accepted_at = COALESCE(updated_at, created_at, NOW())
            WHERE accepted_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_character_sheet_delivered_by_user_id_app_user",
        "character_sheet",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_character_sheet_source_draft_id_party_character_sheet_draft",
        "character_sheet",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_character_sheet_delivered_by_user_id"), table_name="character_sheet")
    op.drop_index(op.f("ix_character_sheet_source_draft_id"), table_name="character_sheet")
    op.drop_column("character_sheet", "accepted_at")
    op.drop_column("character_sheet", "delivered_at")
    op.drop_column("character_sheet", "delivered_by_user_id")
    op.drop_column("character_sheet", "source_draft_id")

    op.drop_index(
        op.f("ix_party_character_sheet_draft_created_by_user_id"),
        table_name="party_character_sheet_draft",
    )
    op.drop_index(
        op.f("ix_party_character_sheet_draft_party_id"),
        table_name="party_character_sheet_draft",
    )
    op.drop_table("party_character_sheet_draft")
    postgresql.ENUM(name="partycharactersheetdraftstatus").drop(op.get_bind(), checkfirst=True)
