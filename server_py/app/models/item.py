from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


class ItemType(str, Enum):
    WEAPON = "WEAPON"
    ARMOR = "ARMOR"
    CONSUMABLE = "CONSUMABLE"
    MISC = "MISC"
    MAGIC = "MAGIC"


class Item(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    name: str
    type: ItemType = Field(sa_column=Column(SAEnum(ItemType), nullable=False))
    description: str
    price: float | None = None
    weight: float | None = None
    damage_dice: str | None = None
    range_meters: float | None = None
    properties: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
