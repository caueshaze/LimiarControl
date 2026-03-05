from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class PurchaseEvent(SQLModel, table=True):
    __tablename__ = "purchase_event"

    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="campaign_session.id", index=True)
    user_id: str | None = Field(default=None, foreign_key="app_user.id", index=True)
    member_id: str = Field(foreign_key="campaign_member.id", index=True)
    item_id: str = Field(foreign_key="item.id", index=True)
    item_name: str  # denormalized for historical accuracy
    quantity: int = Field(default=1)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
