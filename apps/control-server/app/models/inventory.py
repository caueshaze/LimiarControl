from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, String, func
from sqlmodel import Field, SQLModel


class InventoryItem(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    party_id: str | None = Field(default=None, foreign_key="party.id", index=True)
    member_id: str = Field(foreign_key="campaign_member.id", index=True)
    item_id: str = Field(foreign_key="item.id", index=True)
    quantity: int = Field(default=1)
    charges_current: int | None = Field(default=None)
    is_equipped: bool = Field(default=False)
    notes: str | None = None
    source_spell_canonical_key: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True, index=True),
    )
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
