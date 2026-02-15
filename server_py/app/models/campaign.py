from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, String, func
from sqlmodel import Field, SQLModel


class SystemType(str, Enum):
    DND5E = "DND5E"
    T20 = "T20"
    PF2E = "PF2E"
    COC = "COC"
    CUSTOM = "CUSTOM"


class RoleMode(str, Enum):
    GM = "GM"
    PLAYER = "PLAYER"


class Campaign(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    name: str
    join_code: str = Field(
        sa_column=Column(String, unique=True, nullable=False, index=True)
    )
    system: SystemType = Field(sa_column=Column(SAEnum(SystemType), nullable=False))
    role_mode: RoleMode = Field(
        default=RoleMode.GM, sa_column=Column(SAEnum(RoleMode), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
