from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class CombatPhase(str, enum.Enum):
    initiative = "initiative"
    active = "active"
    ended = "ended"


class CombatState(SQLModel, table=True):
    __tablename__ = "combat_state"  # type: ignore[assignment]

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="campaign_session.id", index=True, unique=True)
    phase: CombatPhase = Field(
        default=CombatPhase.initiative,
        sa_column=Column(Enum(CombatPhase, name="combat_phase_enum"), nullable=False),
    )
    round: int = Field(default=1)
    current_turn_index: int = Field(default=0)
    participants: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
