from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class CampaignEntity(SQLModel, table=True):
    __tablename__ = "campaign_entity"  # type: ignore[assignment]

    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    name: str
    category: str = Field(default="npc")
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    image_url: str | None = None
    base_hp: int | None = None
    base_ac: int | None = None
    stats: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    actions: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    notes_private: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    notes_public: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
