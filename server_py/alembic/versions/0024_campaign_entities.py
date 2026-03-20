"""campaign_entities_and_session_entities

Revision ID: 0024_campaign_entities
Revises: 0023_session_command_event
Create Date: 2026-03-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0024_campaign_entities"
down_revision: Union[str, None] = "0023_session_command_event"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Step 1: Evolve npc table into campaign_entity ---
    op.rename_table("npc", "campaign_entity")

    op.drop_index("ix_npc_campaign_id", table_name="campaign_entity")
    op.create_index("ix_campaign_entity_campaign_id", "campaign_entity", ["campaign_id"])

    # Add new columns
    op.add_column("campaign_entity", sa.Column("category", sa.String(), nullable=False, server_default="npc"))
    op.add_column("campaign_entity", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("campaign_entity", sa.Column("image_url", sa.String(), nullable=True))
    op.add_column("campaign_entity", sa.Column("base_hp", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("base_ac", sa.Integer(), nullable=True))
    op.add_column("campaign_entity", sa.Column("stats", JSONB, nullable=True))
    op.add_column("campaign_entity", sa.Column("actions", sa.Text(), nullable=True))
    op.add_column("campaign_entity", sa.Column("notes_private", sa.Text(), nullable=True))
    op.add_column("campaign_entity", sa.Column("notes_public", sa.Text(), nullable=True))

    # Migrate existing data: trait+goal -> description, secret+notes -> notes_private
    op.execute(
        "UPDATE campaign_entity SET "
        "description = COALESCE(trait, '') || ' ' || COALESCE(goal, ''), "
        "notes_private = COALESCE(secret, '') || E'\\n' || COALESCE(notes, '')"
    )

    # Drop legacy columns
    op.drop_column("campaign_entity", "race")
    op.drop_column("campaign_entity", "role")
    op.drop_column("campaign_entity", "trait")
    op.drop_column("campaign_entity", "goal")
    op.drop_column("campaign_entity", "secret")
    op.drop_column("campaign_entity", "notes")

    # --- Step 2: Create session_entity table ---
    op.create_table(
        "session_entity",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("campaign_entity_id", sa.String(), nullable=False),
        sa.Column("visible_to_players", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("current_hp", sa.Integer(), nullable=True),
        sa.Column("overrides", JSONB, nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["session_id"], ["campaign_session.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_entity_id"], ["campaign_entity.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_session_entity_session_id", "session_entity", ["session_id"])
    op.create_index("ix_session_entity_campaign_entity_id", "session_entity", ["campaign_entity_id"])


def downgrade() -> None:
    # Drop session_entity
    op.drop_index("ix_session_entity_campaign_entity_id", table_name="session_entity")
    op.drop_index("ix_session_entity_session_id", table_name="session_entity")
    op.drop_table("session_entity")

    # Restore legacy columns on campaign_entity
    op.add_column("campaign_entity", sa.Column("race", sa.String(), nullable=True))
    op.add_column("campaign_entity", sa.Column("role", sa.String(), nullable=True))
    op.add_column("campaign_entity", sa.Column("trait", sa.String(), nullable=False, server_default=""))
    op.add_column("campaign_entity", sa.Column("goal", sa.String(), nullable=False, server_default=""))
    op.add_column("campaign_entity", sa.Column("secret", sa.String(), nullable=True))
    op.add_column("campaign_entity", sa.Column("notes", sa.String(), nullable=True))

    # Drop new columns
    op.drop_column("campaign_entity", "notes_public")
    op.drop_column("campaign_entity", "notes_private")
    op.drop_column("campaign_entity", "actions")
    op.drop_column("campaign_entity", "stats")
    op.drop_column("campaign_entity", "base_ac")
    op.drop_column("campaign_entity", "base_hp")
    op.drop_column("campaign_entity", "image_url")
    op.drop_column("campaign_entity", "description")
    op.drop_column("campaign_entity", "category")

    # Rename back to npc
    op.drop_index("ix_campaign_entity_campaign_id", table_name="campaign_entity")
    op.rename_table("campaign_entity", "npc")
    op.create_index("ix_npc_campaign_id", "npc", ["campaign_id"])
