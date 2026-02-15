from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, func
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Session(SQLModel, table=True):
    __tablename__ = "campaign_session"
    __table_args__ = (UniqueConstraint("party_id", "sequence_number"),)

    id: str | None = Field(default=None, primary_key=True)
    party_id: str | None = Field(default=None, foreign_key="party.id", index=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    number: int
    sequence_number: int | None = Field(default=None)
    title: str
    join_code: str = Field(
        sa_column=Column(String, unique=True, nullable=False, index=True)
    )
    status: SessionStatus = Field(
        default=SessionStatus.CLOSED,
        sa_column=Column(SAEnum(SessionStatus), nullable=False),
    )
    started_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    ended_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    duration_seconds: int = Field(
        default=0, sa_column=Column(Integer, nullable=False, server_default="0")
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
