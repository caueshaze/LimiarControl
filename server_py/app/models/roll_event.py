from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, JSON, func
from sqlmodel import Field, SQLModel

from app.models.campaign import RoleMode


class RollEvent(SQLModel, table=True):
    __tablename__ = "roll_event"
    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str | None = Field(default=None, foreign_key="campaign.id", index=True)
    session_id: str = Field(foreign_key="campaign_session.id", index=True)
    author_name: str
    role_mode: RoleMode = Field(sa_column=Column(SAEnum(RoleMode), nullable=False))
    label: str | None = None
    expression: str
    count: int
    sides: int
    modifier: int
    results: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    total: int
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
