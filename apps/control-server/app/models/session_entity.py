from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class SessionEntity(SQLModel, table=True):
    __tablename__ = "session_entity"  # type: ignore[assignment]

    id: str | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="campaign_session.id", index=True)
    campaign_entity_id: str = Field(foreign_key="campaign_entity.id", index=True)
    visible_to_players: bool = Field(default=False)
    current_hp: int | None = None
    overrides: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    label: str | None = None
    revealed_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
