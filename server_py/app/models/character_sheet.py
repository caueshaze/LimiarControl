from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class CharacterSheet(SQLModel, table=True):
    __tablename__ = "character_sheet"  # type: ignore[assignment]

    id: str = Field(primary_key=True)
    party_id: str = Field(foreign_key="party.id", index=True)
    player_user_id: str = Field(foreign_key="app_user.id", index=True)
    data: dict = Field(sa_column=Column(JSONB, nullable=False))
    source_draft_id: str | None = Field(
        default=None,
        foreign_key="party_character_sheet_draft.id",
        index=True,
    )
    delivered_by_user_id: str | None = Field(
        default=None,
        foreign_key="app_user.id",
        index=True,
    )
    delivered_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    accepted_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
