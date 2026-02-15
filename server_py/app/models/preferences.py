from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class Preferences(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="app_user.id", index=True)
    selected_campaign_id: str | None = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
