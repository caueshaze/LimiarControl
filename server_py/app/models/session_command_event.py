from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class SessionCommandEvent(SQLModel, table=True):
    __tablename__ = "session_command_event"  # type: ignore[assignment]

    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="campaign_session.id", index=True)
    user_id: str | None = Field(default=None, foreign_key="app_user.id", index=True)
    member_id: str = Field(foreign_key="campaign_member.id", index=True)
    actor_name: str | None = None
    command_type: str = Field(index=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
