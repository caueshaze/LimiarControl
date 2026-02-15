from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class SessionState(SQLModel, table=True):
    __tablename__ = "session_state"

    id: str | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="campaign_session.id", index=True)
    player_user_id: str = Field(foreign_key="app_user.id", index=True)
    state_json: dict = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
