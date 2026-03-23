from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class CampaignEntity(SQLModel, table=True):
    __tablename__ = "campaign_entity"  # type: ignore[assignment]

    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    name: str
    category: str = Field(default="npc")
    size: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    creature_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    creature_subtype: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    image_url: str | None = None
    armor_class: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    max_hp: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    speed_meters: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    initiative_bonus: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    abilities: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    saving_throws: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    skills: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    senses: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    spellcasting: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    damage_resistances: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    damage_immunities: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    damage_vulnerabilities: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    condition_immunities: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    combat_actions: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    actions: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    notes_private: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    notes_public: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
